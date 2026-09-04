### Vendas incompletas são selecionaveis
Preciso que vendas incompletas sejam explicitamente bloqueadas antes da emissão. Para facilitar essa tarefa monte uma validação QUE SÓ RODA COM O MODULO FISCAL ATIVADO, essa validação ira validar uma venda sempre que esta for finalizada, indicando se ela pode servir como base para emissão fiscal ou não. Antes da emisão ela deve passar normamelmente pela validação de todos os seus dados desde as informações de operação até a conferencia de integridade dos itens.
Este bloqueio deve ser mostrado explicitamente no modal de seleção e deve emitir um toast explicando os erros com uma formatação bonitinha.

### Bloquear a multipla emissão de uma mesma venda
Quero que você analise o sistema e veja como a gente bloqueia a emissão de uma mesma venda. O certo seria bloquear mais uma requisição quando a venda ja foi emitida. Não sei como tratar esse campo para isso preciso que voce me retorne as possibilidades.