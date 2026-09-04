# contexto
Conseguimos abranger boa parte das necessidades fiscais envolvidas nos modulos de PRODUTO, SERVICOS, VENDAS E ORDENS DE SERVICO. No entanto, devemos elevar um pouco mais a maturidade das funcionalidades e experiencia do sistema, aplicando erros mais intuitivos, mapeamento de campos, classificacao de unidades, mascaras numericas e etc...

# atualizacoes
1- Aplicar atualizacao no **BaseSelect.vue** (C:\dev\bigpdv\frontend\src\shared\components\ui\BaseSelect\BaseSelect.vue) -> 
    Preciso que adicione mais uma funcionalidade nesse select, para quando clicar novamente em cima do select, este feche suas opcoes. Hoje isso ainda nao funciona, funciona apenas o clickoutside e selecionar;
2- Adicionar erros de zod diretamente nos campos invalidos, ou que retornaram erros do backend;
3- Os campos CST e CSOSN dos modulos de produto e servico devem ser automaticamente mapeados de acordo com o regime tributario cadastrado nos dados da empresa;
4- GTIN deve ter uma caixa de selecao que permite vincular o codigo com o codigo de barras do produto (padrao EAN);
5- Aplicar mascaras para o campo de lc 116 e relacionados em servicos;
6- Aplicar uma predefinacao de unidades nos modulos de produto e servico, utilizando o BaseSelect.vue assim como o campo de 'origem' e etc. ->
    Campos observados e sugestoes:
        PRODUTOS -> Unidade Tributavel -> N (Unidade), KG (Quilograma), CX (Caixa), PCT (Pacote), L (Litro);
        SERVICOS -> Unidade Tributavel -> SV (se você cobrou por um projeto fechado de software) ou HR (se o contrato prevê cobrança por horas de desenvolvimento gastas);

# correcao
1- No modal de vendas os selects para os campos fiscais como 'finalidade da emissao' e 'indicador de presenca' nao estao aparecendo em sua integridade, se classificando como erro de UI.

# Detalhes sobre o planejamento
1- Qualquer duvida ou sugestao de melhoria deve ser perguntada a mim;
2- Garanta integridade nas atualizacoes;
3- Faca um planejamento detalhado, explicando o passo a passo de cada alteracao;