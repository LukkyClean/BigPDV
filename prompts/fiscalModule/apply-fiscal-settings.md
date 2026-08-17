# Contexto
O ERP StartBig está se consolidando e precisa de um novo módulo fiscal, esse módulo, por sua vez, deve ser altamente seguro e aparecer apenas para as licenças com o acesso ao recurso, além de controlar o acesso granular dos usuários permitidos a fazer essas trasanções.

# Como funcionará o processo
Seu trabalho nesse chat é analisar e aplicar a implementação inicial analisada no documento enviado (**startbig-modulo-fiscal-design.pdf**). Esse documento por sua vez, possui apenas uma idealização inicial de como devemos começar a implementar os atributos fiscais da aplicação.

## Regras da implementação
Focaremos apenas em incrementar de forma segura as tableas e campos necessários em PRODUTOS, SERVIÇOS, VENDAS e OS. Faremoas as validações necessárias, conforme o documento, e toda a preparação para o envio à API StartBIG da Web, feature essa que ainda não está no escopo atual.

### Guia de implementação:
1- Adicionar as tabelas necessárias
2- Adicionar os campos no frontend
3- Garantir o acesso exclusivo dos usuários e licenças permitidas ao recurso
4- Esconder a UI das licenças que não possui backups no plano

OBS: Não lembro se temos como saber qual é o plano ou permissões da licença, caso não tenha essa informação tente preparar a estrutura para esse bloqueio.

### Regras cruciais
1- Segurança em primeiro lugar --> Não podemos permitir acesso não autorizado na rota de emissão fiscal, devemos garantir essa segurança;
2- UI não aparece para quem não precisa;
3- Validações devem ser feitas a todo momento;
4- Tente garantir Fast Break na camada de validação;

# Sobre Planejamentos e este chat
Preciso deixar claro que o envio do documento com toda a implementação não significa incluir tudo de uma vez, preciso trabalhar toda essa feat passo a passo, seguindo fluxo lógico e implementando as mudanças módulo por módulo. Portanto jamais tente resolver toda a implementação de uma única vez, priorize o a divisão em partes e uma conversa fluída comigo.

Garanta que todas as decisões tomadas por você passe pela minha supervisão

### Skills
Skills para backend e frontend estão sendo anexada para você entender um pouco mais do que eu espero da implementação.

### Estou enviando apenas um planejamento inicial
O documento enviado não deve ser tratado como veradade absoluta, sei que em momento de implementação aparece muitos erros complexos que podem ter soluções melhores que a proposta. Por isso, peço gentilmente que sempre tente aplicar a solução do melhor jeito possível, respeitando as dependências da minha aplicação.