# Contexto
Com base na alterações feitas nos módulos de Produto, Serviço, Vendas e OS foi observado que precisa de algumas alterações na parte visual da aplicação para manter a concordância e integridade com as funções do sistema. 

# Alterações propostas

### Alterações críticas

1- Botões para salvar dados fiscais/configuração fiscal -> Estes botões são um ataque crítico a experiência, pois toda e qualquer alteraço deve passar pelo botão principal de salvar alterações. Portanto, retire esse botão de salvar dados fiscais presente em todos os módulo e utilize os botões principais que salvam todos os outros dados também.
2- Placeholders dos campos fiscais parecem dados cadastrados -> Produtos e serviços sem dados cadastrados dão a impressão que têm, esta causanda pelos placeholders.
3- Nota fiscal em OS deve ter uma section própria assim como dados, itens e detalhes de OS -> Adicione uma seção para fiscal em OS.

### Alterações de design

4- Os campos de fiscais em produtos e serviços estão com um header com ícone fora do padrão -> mantenha a mesma cor, fundo e tamanho dos demais.
5- Adicione dicas sobre os dados fiscais, informando a importância do cadastro para a emissão de NF e outros dados fiscais -> Isto em Produtos e Serviços.