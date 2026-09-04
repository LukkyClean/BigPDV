Você é um especialista em arquitetura backend e legislação fiscal brasileira.
Sua tarefa é implementar o módulo autônomo `FiscalTaxEngine`.

# Requisitos Técnicos:
1. **Separação de Camadas**: O módulo deve ser 100% desconectado da camada HTTP ou Banco de Dados, focando na lógica de cálculo e DTOs, e estando devidamente separado como um modulo acessivel e escalavel para o servico de emissao fical.
2. **Precisão Numérica**:
   - Utilize arredondamento bancário/financeiro (ROUND_HALF_UP) para 2 casas decimais.
   - Trate eventuais diferenças de centavos resultantes do rateio ajustando no item de maior valor bruto.
3. **Tratamento de Exceções**: Lance exceções personalizadas (ex: `InvalidTaxConfigurationException`) quando dados obrigatórios (NCM, CFOP, CRT) estiverem ausentes ou inconsistentes.

# Contexto
Hoje vamos implementar um modulo responsavel por todo calculo fiscal necessario da minha aplicacao e preciso que voce me ajude a alcancar meu objetivo de forma profissional e organizada. Espero que voce seja capaz de me perguntar e planejar a implementacao de forma inteligente, se direcionando passo a passo em prol do objetivo final.

## Foco total em calculos para emissao de NF-e
Nosso objetivo e calcular os tributos importantes para emissao de NF-e que exigem os calculos presumidos. Para um melhor desempenho ja organizei um documento que especifica minhas necessidades, mas porfavor nao perca tempo em fazer um acesso a propria documentacao da FocusNF, que e a api que iremos utilizar para emissao, com intuito de enteder as necessidades de dos calculos com base na situacao atual do sistema.
Focus NF-e doc -> https://doc.focusnfe.com.br/reference/emitir_nfe
Nome do arquivo anexado com o planejamento inicial -> remodelacao-nfe.md

# Como voce deve implementar 
1- Como a base para esses calculos preciso adicionar os campos PIS, CONFINS e IPI para os produtos quando a ST requere esses campos -> Preciso que esses campos aparecam e desaparecam de forma dinamica conforme a ST e necessidade. 
2- Analisar o planejamento inicial e juntar com os dados recolhidos da sua pesquisa na propria focus.
3- Implementar esse modulo fical com base na sua resposta da analise final. -> Esse modulo deve ser totalmente modular e escalavel e existe apenas no backend.
4- Fazer validacoes rigorosas e retornar erros explicitos quando algum campo ou calculo tenha dado errado -> Aqui nao podemos deixar nenhuma duvida ao usuario.
5- Aplicar cada calculo do planejamento inicial de forma funcional e juntar todo o processo atraves de um service organizado que monta a resposta final com os dados necessarios.

# Como tratar esse prompt
1- Peco que me pergunte sobre qualquer duvida
2- Preciso que voce acrescente necessidade somenete se for PRECISO
3- Quero que voce seja capaz de resolver conflitos mas sempre me especificando o problema e perguntando como resolver. 

# Objetivo final que voce deve alcancar
Se resume em um modulo profissional que consegue preparar todos os calculos tributarios necessarios para a emissao de uma NF-e com base em validacoes rigorosas e tratamento explicito de Situacao Tributaria e codigos de UF. 

## Problema
Como vamos resolver a mudanca constante das aliquotas??

## Informacao exta 
Atenção para ICMS-ST / MVA: Se houver Substituição Tributária (CST 10, 30, 70), aplica-se a Margem de Valor Adicionado (MVA) sobre a base para calcular o ICMS-ST (icms_base_calculo_st, icms_aliquota_st, icms_valor_st).
Redução de Base: Quando há benefício fiscal, calcula-se o percentual de redução antes de aplicar a alíquota.