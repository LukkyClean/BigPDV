"""
As rotas fiscais fora do router /fiscal não podem se destrancar sozinhas.

O buraco: `requer_modulo_fiscal` perguntava só "esta empresa configurou?", e
respondia isso pela EXISTÊNCIA da linha EmpresaFiscalSettings. Só que
`GET /empresas/` cria essa linha para qualquer usuário autenticado -- e essa
rota é chamada ao abrir configurações ou ao vender no PIX. Bastava usar o
sistema normalmente para o gate passar a liberar.

O router /fiscal nunca teve esse problema (tem `requer_modulo("NFE")`), mas as
13 rotas fiscais que moram em produto, serviço, venda e OS dependem só desta
função -- inclusive PUTs que gravam NCM, CFOP e CST.

Achado pelo Carlos André em 07/09/2026.
"""

import pytest
from fastapi import HTTPException

from app.core.depends import requer_modulo_fiscal


class _SettingsExistentes:
    """Simula a linha que o `GET /empresas/` cria sozinho."""

    modulo_fiscal_ativo = True

    def filter(self, *_a, **_k):
        return self

    def first(self):
        return self


class _DbComSettings:
    """Sessão em que EmpresaFiscalSettings JÁ existe para a empresa."""

    def query(self, *_a, **_k):
        return _SettingsExistentes()


@pytest.fixture
def _sem_licenca(monkeypatch):
    """Licença sem módulo nenhum -- o caso de toda loja em campo hoje."""
    from app.core import modulos as modulos_mod

    monkeypatch.setattr(
        modulos_mod.licenca_service, "modulos_da_licenca", lambda _db: []
    )


@pytest.fixture
def _licenca_com_nfe(monkeypatch):
    from app.core import modulos as modulos_mod

    monkeypatch.setattr(
        modulos_mod.licenca_service, "modulos_da_licenca", lambda _db: ["NFE"]
    )


def test_linha_criada_sozinha_nao_destranca_o_fiscal(_sem_licenca):
    """O coração do bug: linha existe, licença não concede -> continua barrado.

    Antes da correção este caso LIBERAVA, porque só se olhava a existência da
    linha. Se este teste voltar a passar por engano, qualquer loja poderá
    gravar dados fiscais sem ter contratado.
    """
    with pytest.raises(HTTPException) as exc:
        requer_modulo_fiscal(
            usuario_token={"empresa_id": 1}, db=_DbComSettings()
        )

    assert exc.value.status_code == 403
    assert exc.value.detail["codigo"] == "MODULO_NAO_CONTRATADO"


def test_com_licenca_e_configurado_libera(_licenca_com_nfe):
    """Contratado E configurado: passa, devolvendo o token para encadear."""
    token = {"empresa_id": 1}
    assert requer_modulo_fiscal(usuario_token=token, db=_DbComSettings()) is token


def test_contratado_mas_sem_configurar_pede_configuracao(_licenca_com_nfe):
    """Contratado e ainda não configurado é estado normal de quem liberou agora.

    Tem que responder 403 pedindo configuração -- e NÃO o de não contratado,
    senão o dono vai atrás do vendedor em vez de ir na tela de certificado.
    """

    class _DbVazio:
        def query(self, *_a, **_k):
            class _Q:
                def filter(self, *_a, **_k):
                    return self

                def first(self):
                    return None

            return _Q()

    with pytest.raises(HTTPException) as exc:
        requer_modulo_fiscal(usuario_token={"empresa_id": 1}, db=_DbVazio())

    assert exc.value.status_code == 403
    assert "configurado" in str(exc.value.detail).lower()


def test_usuario_sem_empresa_barra(_licenca_com_nfe):
    with pytest.raises(HTTPException) as exc:
        requer_modulo_fiscal(usuario_token={}, db=_DbComSettings())

    assert exc.value.status_code == 403
