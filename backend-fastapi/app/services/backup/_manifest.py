from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from ._constants import INTEGRITY_CHECK_OK


@dataclass
class ManifestBuilder:

    manifest_version: int = 2
    tipo: str = "full"
    base: Optional[str] = None
    criado_em: str = field(default_factory=lambda: datetime.now().isoformat())
    app: str = "StartBigERP"
    integrity_check: str = INTEGRITY_CHECK_OK
    arquivos: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def add_file(
        self,
        arcname: str,
        sha256: str,
        size: int,
        mtime_ns: int,
        origin: str,
    ) -> None:
        self.arquivos[arcname] = {
            "sha256": sha256,
            "tamanho": size,
            "mtime_ns": mtime_ns,
            "origem": origin,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "tipo": self.tipo,
            "base": self.base,
            "criado_em": self.criado_em,
            "app": self.app,
            "integrity_check": self.integrity_check,
            "arquivos": self.arquivos,
        }
