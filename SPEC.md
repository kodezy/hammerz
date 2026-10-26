# Hammerz — Especificação completa do MVP

**Versão:** 0.7 — revisão de consistência em 26/10/2026; cadastro, cancelamento sem lances, catálogo e rotas operacionais alinhados; USD fixo e temas claro/escuro preservados  

**Status:** especificação consolidada para implementação e validação; não representa código, deploy ou testes de execução já concluídos  
**Prazo oficial:** 7 dias corridos desde o recebimento do desafio. Prazo restante informado em 26/10/2026: 3–4 dias. A data e hora do e-mail original são a referência da entrega; o prazo relativo não se renova com esta revisão.  
**Orçamento:** sem contratação de serviços pagos ou compra de domínio; usar o servidor já disponível. Energia, conexão e manutenção desse servidor são recursos existentes, não uma promessa de infraestrutura sem custo operacional.



## 1. Objetivo e escopo

Criar uma casa de leilões online de obras de arte importadas de uma API pública. Leiloeiros publicam seus lotes; licitantes depositam saldo simulado e disputam os itens por lances ao vivo. Qualquer pessoa pode consultar a auditoria de um lote e abrir um comprovante compartilhado, sem login.

### 1.1 Requisitos obrigatórios 

- Autenticação e autorização com os papéis leiloeiro e licitante; leiloeiros não dão lances.
- Busca de itens na API pública e criação de lotes com imagem, título, atributos, lance inicial, incremento mínimo, início e fim.
- Vitrine separando lotes agendados, ao vivo e encerrados, sem mostrar cancelados.
- Painel do leiloeiro com gerenciamento dos próprios lotes, cancelamento antes do primeiro lance, resultados e total recebido.
- Sala com lance atual, histórico, posição do usuário, indicador de liderança e contador atualizado sem recarregar a página.
- Carteira com saldo total, comprometido, disponível e depósito simulado.
- Regras de lance, reserva/liberação de saldo, anti-sniping e liquidação.
- Histórico de participações e arremates, com comprovante público compartilhável.
- Auditoria pública capaz de detectar alterações, inserções e remoções posteriores no histórico, inclusive diretamente no banco, sem expor dados pessoais.
- Vitrine, sala, auditoria e comprovante funcionam quando a API de itens está indisponível.
- Deploy público, repositório GitHub público, README e dados de demonstração.

### 1.2 Decisões e extras incluídos

- **[DECISÃO]** Cadastro público apenas de licitantes, além das contas de avaliação previamente provisionadas com saldos existentes e login convencional; sem confirmação de e-mail no MVP.
- **[EXTRA INCLUÍDO]** Cancelamento de lotes com lances antes do encerramento vigente, com liberação da reserva do líder e motivo público obrigatório.
- **[EXTRA INCLUÍDO]** Docker Compose e testes automatizados das regras críticas.
- **[DECISÃO]** Interface de produto em inglês, sem modo ou atalhos de demonstração; contas de avaliação acessadas pelo login convencional e credenciais fornecidas somente no README.
- **[DECISÃO]** USD é a moeda fixa da aplicação, sem seletor, preferência de moeda ou câmbio; valores exibidos no padrão `en-US`.
- **[EXTRA INCLUÍDO]** Tema escuro opcional, escolhido pelo usuário; tema claro por padrão e preferência persistida somente no navegador. Os dois temas usam as mesmas telas e componentes.
- **[DECISÃO]** Dinheiro em centavos inteiros de USD; datas em UTC; monólito modular; uma instância e um processo de API.
- **[DECISÃO]** Evidência de auditoria em diário persistente no servidor, fora do PostgreSQL e inacessível pelas credenciais do banco.
- **[DECISÃO]** Se não for possível persistir ou verificar essa evidência, recusar novos lances temporariamente. Consultas continuam disponíveis com estado de verificação explícito.

### 1.3 Fora do escopo e cortes de prazo

Pagamentos reais, nota fiscal, transferência livre entre usuários, revenda, aplicativo nativo, recuperação de senha, confirmação de e-mail, cadastro público de leiloeiros, administração complexa, múltiplas réplicas e alta disponibilidade.

Busca e filtros avançados da vitrine e gráficos são opcionais não comprometidos para esta versão. A alternância claro/escuro foi incluída por decisão de produto na seção 4.5. A busca no catálogo externo e as abas por situação da vitrine continuam obrigatórias. Não cortar auditoria, concorrência, liquidação, demonstração ou deploy para incluir acabamento opcional.

## 2. Stack, arquitetura e execução

| Camada | Escolha |
| --- | --- |
| Frontend | React, TypeScript, Vite e Tailwind CSS |
| Dados no frontend | TanStack Query e estado local para interface |
| Backend | Python 3.12, FastAPI e Pydantic v2 |
| Persistência | PostgreSQL 16, SQLAlchemy 2 e Alembic |
| Tempo real | WebSocket FastAPI; REST fornece o estado autoritativo |
| Catálogo | Metropolitan Museum of Art Collection API |
| Autenticação | Argon2 e JWT Bearer de curta duração |
| Auditoria | HMAC-SHA256, eventos canônicos e diário externo JSONL com sincronização durável |
| Servidor web | Caddy para arquivos estáticos, proxy REST/WS e HTTPS |
| Execução | Docker Compose no servidor próprio |
| Qualidade | Ruff, pytest, build TypeScript/Vite e GitHub Actions |

O navegador acessa um único endereço. Caddy serve o build React, encaminha `/api/*`, `/ws/*` e `/health/*` para o backend e mantém o fallback da SPA somente para as demais rotas de navegação. Preservar esses prefixos no proxy; health checks devem retornar o status HTTP/JSON do backend, nunca o HTML da SPA. O banco fica apenas na rede interna do Compose. O backend consulta a API do museu durante busca/importação; lotes publicados usam snapshots locais.

### 2.1 Serviços e volumes

- `web`: Caddy e build estático do frontend; publica apenas as portas necessárias ao HTTP/HTTPS.
- `backend`: FastAPI com um worker Uvicorn, WebSockets em memória e tarefa de encerramento no lifespan.
- `postgres`: dados persistentes; sem porta pública.
- Volumes persistentes separados: `postgres_data`, `audit_data` e dados/configuração de certificados do Caddy.
- Nenhum volume de auditoria ou segredo HMAC é montado no container PostgreSQL.
- Volumes de dados não pertencem ao ciclo de rebuild da aplicação; não usar `docker compose down -v` como procedimento normal.

Não adicionar Redis, fila externa, microsserviços ou orquestrador de containers neste MVP. O diário é um módulo local da aplicação, não um novo serviço distribuído.

### 2.2 Endereço público e HTTPS

**[DECISÃO]** Usar hostname gratuito baseado no IP público, no formato `<public-hostname>`, e Caddy para obtenção/renovação de certificado. A URL concreta será registrada no README depois do deploy; o texto entre sinais de menor/maior é um placeholder, não um hostname utilizável.

Pré-condições de entrega: resolução DNS correta, portas necessárias acessíveis, certificado confiável pelo navegador, WSS funcionando, IP estável durante a avaliação e servidor ligado. Validar tudo a partir de uma conexão externa. A emissão do certificado está sujeita às condições do serviço e da autoridade certificadora; não considerar HTTPS concluído apenas pela configuração.

Não depender de túnel temporário nem de URL que muda a cada reinício. Endereço e exposição pública do servidor são conhecidos; SSH administrativo pode continuar restrito à VPN.

## 3. Papéis, cadastro e autenticação

| Ação | Visitante | Leiloeiro | Licitante |
| --- | :---: | :---: | :---: |
| Vitrine, sala, histórico público e auditoria | Sim | Sim | Sim |
| Abrir comprovante compartilhado | Sim | Sim | Sim |
| Criar e gerenciar lotes próprios | Não | Sim | Não |
| Cancelar lote próprio elegível | Não | Sim | Não |
| Consultar resultados e total recebido próprio | Não | Sim | Não |
| Depositar saldo simulado e dar lances | Não | Não | Sim |
| Ver carteira, participações e arremates próprios | Não | Não | Sim |

### 3.1 Cadastro

- Tela `/register` pede e-mail, senha e confirmação de senha. A API recebe e valida e-mail e senha; a confirmação é validada na interface.
- Normalizar e-mail com política única e documentada; unicidade garantida no banco, inclusive sob cadastro concorrente.
- Senha entre 8 e 128 caracteres; hash Argon2. Não registrar senha ou token em logs.
- Novo usuário sempre recebe papel `BIDDER` e carteira com saldo zero. Ignorar/rejeitar tentativa de escolher `SELLER`, saldo ou ID de usuário.
- Cadastro e criação da carteira ocorrem na mesma transação. E-mail já cadastrado recebe erro claro.
- Leiloeiros são criados por seed ou comando administrativo local; não há promoção pública de papel.
- Não existe envio de e-mail, recuperação de senha ou confirmação de endereço neste MVP. Documentar no README que os créditos são simulados e não há processamento de pagamentos reais. Na interface, usar os nomes de produto da seção 4.2.

### 3.2 Sessão

- Login retorna JWT Bearer com expiração de 30 minutos; validar assinatura, expiração e algoritmo permitido.
- Token permanece em memória no frontend; recarregar a página exige novo login. Sem refresh token nesta versão. Essa limitação da sessão é intencional no MVP e não apaga contas, saldos ou operações. Nunca persistir JWT em localStorage/sessionStorage.
- Após autenticação, carregar `/api/v1/auth/me` antes de renderizar navegação privada. Sem `returnTo` permitido, `SELLER` segue para `/seller` e `BIDDER` para `/`. Aceitar `returnTo` apenas como caminho interno autorizado para aquele papel; nunca URL externa.
- Cadastro bem-sucedido leva a `/login?returnTo=/wallet`, com confirmação `Account created. Sign in to continue.`. Somente após login válido e `/auth/me`, abrir a carteira zero; `/wallet` é um destino interno autorizado para o novo licitante. Não autenticar automaticamente nem inserir crédito inicial em cadastro público.
- Em `401`, preservar metadados de operações incertas, limpar token/caches de sessão e pedir autenticação antes do retry. Páginas públicas continuam disponíveis como visitante.
- Logout remove o token e limpa os caches privados da sessão. Respostas de outra sessão não podem permanecer visíveis após troca de conta.
- Autorizações e propriedade do lote são verificadas no servidor. IDs enviados pelo cliente não definem a identidade do ator.
- Rate limiting em cadastro, login, depósito e lance; `401` para sessão ausente/expirada e `403` para papel ou propriedade indevidos.

## 4. Jornadas e telas

| Rota | Conteúdo mínimo |
| --- | --- |
| `/` | Abas Agendados, Ao vivo e Encerrados; cards com imagem, título, valor de referência e horários; cancelados omitidos |
| `/login` | E-mail e senha, erros e acesso ao cadastro; autenticação convencional, sem credenciais expostas ou botões de contas prontas |
| `/register` | Cadastro público de licitante com validações; nova carteira começa em $0.00 USD |
| `/seller` | Busca no museu, seleção de item, criação de lote, gestão própria, cancelamento, resultados e total recebido |
| `/lots/:id` | Snapshot da obra, lance atual ou inicial, incremento, contador, histórico, formulário e posição do usuário |
| `/wallet` | Total balance, Committed, Available to bid e Add funds; todos os valores em USD |
| `/my-wins` | Participações e vitórias; status do lote, valor final e links dos comprovantes |
| `/lots/:id/audit` | Histórico completo, cancelamento/motivo quando houver e resultado da verificação |
| `/receipts/:id` | Comprovante público com obra, vencedor pseudonimizado, valor, horário e link para auditoria |

### 4.1 Comportamento da interface

- Visitantes acompanham a sala sem login; formulário de lance exige sessão de licitante.
- Estado pessoal distingue `NOT_PARTICIPATING`, `LEADING`, `OUTBID`, `WON`, `LOST` e `CANCELLED`, conforme aplicável. Sem lance próprio, não mostrar “você foi superado”.
- Mostrar motivo específico de recusa: abaixo do mínimo, saldo insuficiente, já líder, não iniciado, encerrado, cancelado ou auditoria indisponível.
- “Ao vivo”, “agendado” e contador usam horário do servidor, recalibrado a cada snapshot. O relógio local não decide se um lance é válido.
- No zero do contador, atualizar o estado por REST; até liquidação concluída, mostrar “Finalizando”.
- Conexão perdida tem aviso visível e reconexão automática. Não apresentar lance como aceito apenas por atualização otimista.
- Em operação com resultado incerto, mostrar `Confirmation pending` e repetir a mesma chave e payload conforme seção 6.3; não criar automaticamente outra tentativa. Preservar os metadados antes do envio para permitir reconciliação após recarga e novo login.
- Lote cancelado continua acessível por URL direta, nos históricos dos participantes e na auditoria, com data e motivo. Não oferece formulário de lance ou comprovante de arremate.
- Interface em inglês, legível em desktop e celular; valores em USD com formatação `en-US` e horários no fuso local identificado. Não colocar detalhes internos de HMAC, locks ou containers no fluxo normal do usuário.


### 4.2 Apresentação de produto e acesso às contas [DECISÃO]

- USD é fixo e implícito nos fluxos: não mostrar seletor de moeda, bandeira, dropdown, chevron ou badge solto de USD no cabeçalho. Usar `$1,500.00` nos valores; identificar USD apenas onde necessário ao contexto financeiro, como rótulo de entrada e comprovante público.
- O produto se apresenta como Hammerz, com fluxos convencionais de uma plataforma de leilões. Não há modo demo, seletor de personagem/papel, botão de entrada automática ou área “Explore the demo”.
- `/login` usa somente `Email`, `Password` e `Sign in`, com link `Create account`. Credenciais de avaliação ficam no README, sem preenchimento automático ou exposição na tela pública.
- As contas pré-criadas usam o mesmo endpoint de login, hash de senha, JWT, permissões e persistência das demais contas. Não criar autenticação especial, bypass ou endpoint de login como outro usuário.
- O saldo já existe na carteira quando uma conta provisionada entra. Login, logout, recarga de página e reinício da aplicação não concedem créditos, restauram valores iniciais ou apagam participações.
- A carteira mostra `Total balance`, `Committed`, `Available to bid` e a ação `Add funds`; confirmação: `Funds added`. Não usar `Demo wallet`, `Add demo funds`, `Demo bidder`, `Demo seller` ou badges/banners de demonstração.
- O depósito continua sendo simulado, conforme o enunciado. Não pedir cartão ou dados bancários. No contexto da confirmação de adição de saldo, informar discretamente `No payment will be processed.`; o README explica a natureza técnica do ambiente. Não acrescentar integração de pagamento real ao escopo.
- O cadastro público continua disponível e cria carteira com saldo zero; os saldos pré-existentes pertencem apenas às contas previamente provisionadas da seção 13.


### 4.3 Contrato de UI/UX e navegação

| Contexto | Navegação e ações |
| --- | --- |
| Visitante | `Auctions`, `Sign in` e acesso ao cadastro; sala, auditoria e recibo públicos. Sem saldo, alias privado, `Sign out` ou formulário ativo de lance. |
| Licitante | `Auctions`, `My Bids & Wins`, `Wallet`, `Sign out`; formulário de lance somente quando elegível. Sem navegação de gerenciamento do vendedor. |
| Leiloeiro | `Auctions`, `Seller dashboard`, `Sign out`; gerencia somente os próprios lotes. Não mostrar `Wallet`, participações privadas de licitante ou botão de dar lance. |

- A autorização no backend continua obrigatória mesmo quando a ação está oculta na interface. A sala do próprio lote mostra `You own this lot` e a ação de cancelamento quando elegível; navegar para ela não troca o papel do usuário.
- Cada card, linha de participação, painel de gestão, sala, recibo e auditoria carrega o `auction_id` do item escolhido. Título não é chave: lotes diferentes podem usar a mesma obra. Mostrar `Lot 001`, `Lot 002` etc. como referência de apresentação; a API usa UUIDs.
- `View public audit` em um comprovante sempre abre a auditoria do lote daquele comprovante. `Manage lot` abre a sala do lote para o vendedor; cancelamento exige ação e confirmação explícitas, nunca ocorre por abrir o gerenciamento.
- Em `NOT_PARTICIPATING`, mostrar `Place your first bid`; em `OUTBID`, `You have been outbid` e a liberação da reserva anterior; em `LEADING`, mostrar o valor reservado e ocultar o formulário editável. Um botão desabilitado `You are already leading` pode ocupar seu lugar. O próximo mínimo exibido, quando aplicável, é sempre lance atual + incremento.
- Uma transição de lance confirmado atualiza valor, alias líder, sequência, quantidade de lances, posição privada, reserva e saldo a partir do mesmo estado autoritativo. Não combinar o cabeçalho do lance novo com o histórico anterior.
- Após depósito confirmado, `Back to wallet` e a navegação para a carteira mostram os valores novos. Navegação não restaura saldos anteriores. Após lance, cancelamento ou liquidação, refazer as consultas financeiras pertinentes; não deduzir tudo de um valor estático da tela.
- Uma ação com `confirmation_pending=true` não recebe mensagem definitiva de sucesso. Durante falha de conexão, preservar o último estado identificado como desatualizado e bloquear novo envio até reconciliar o estado da sala; consultas públicas continuam disponíveis.
- A auditoria de lote cancelado mantém o histórico completo, aliases, último lance, data e motivo do cancelamento. `Cancelled` não implica adulteração; um lote cancelado pode estar `Verified`.
- O comprovante distingue o resultado financeiro `Settled` do resultado de integridade `Verified`, `Changes detected` ou `Unable to verify`, com `checked_at`. Nos dois últimos casos mostrar alerta visível; não apresentar o documento como prova de arremate validada.
- Compartilhamento copia a URL pública do recibo somente quando a operação de clipboard for concluída. Se clipboard estiver indisponível, mostrar URL selecionável; manter os dados do mesmo recibo após a confirmação.

### 4.4 Responsividade, imagens e cobertura de estados

- Desktop e mobile oferecem os mesmos dados essenciais e ações de negócio. Recibo mobile inclui lote, obra, autor, vencedor por alias, USD, valor, horário de liquidação com fuso, situação da auditoria e compartilhamento. Cadastro, cancelamento e carregamento do histórico também funcionam no celular.
- Imagens nunca são esticadas: preservar proporção natural. Na sala e no recibo, usar `object-fit: contain` para mostrar a obra integral; cards/hero podem usar `cover` com recorte intencional, sem deformar. Um placeholder preserva o espaço e os metadados se a imagem não carregar.
- Estados de vitrine: `Live`, `Upcoming`, `Ended` e vazio de cada aba. `Finalizing` aparece em `Ended` com indicação própria. Cancelados não aparecem na vitrine pública.
- Abas de participações: `Active bids` inclui participações em lotes não terminais, inclusive `Finalizing`; `Won` inclui somente vitórias com liquidação e confirmação externa concluídas; `Past auctions` inclui derrotas e cancelamentos. Contagens e linhas devem corresponder à aba selecionada.
- Cobrir busca em carregamento, sem resultado e indisponível; login inválido/sessão expirada; cadastro inválido/e-mail existente; carteira zero; depósito pendente/confirmado/recusado; lance recusado/pending/leading/outbid; lote agendado/finalizando/encerrado/cancelado; auditoria nos três resultados.
- Campos informam validações junto ao erro e preservam dados aproveitáveis. Botões com envio em andamento ficam desabilitados. Usar foco visível, rótulos associados, navegação por teclado e mensagens de estado acessíveis; status não depende apenas de cor.
- Penpot é referência editável de telas e transições finitas, não execução do backend. Cada frame informa, em metadados ou documentação de design, lote, papel e estado representados. Links do protótipo não substituem autenticação, mutações, clipboard ou paginação reais.
- Nos fluxos conectados do protótipo, não trocar obra/lote, fazer o saldo voltar ao anterior no retorno da confirmação ou declarar um lance aceito sem refletir seu histórico. Os valores dinâmicos de execução vêm da API, não dos números desenhados no Penpot.

### 4.5 Aparência: tema claro e escuro [EXTRA INCLUÍDO]

- Tema claro é o padrão. Oferecer um único botão de alternância entre `light` e `dark`, disponível para visitantes, licitantes e leiloeiros, inclusive nas telas de autenticação e documentos públicos. No celular, usar botão compacto sem prejudicar o menu. Não adicionar página de configurações, terceira opção `System` ou preferência no backend.
- O controle tem nome acessível dinâmico `Switch to dark mode` ou `Switch to light mode`, `aria-pressed` indicando se o tema escuro está ativo, área de toque de pelo menos 40 × 40 px e foco visível. Funciona por teclado; um tooltip pode explicar o ícone. No Penpot, o componente representa a ação; a troca global do canvas usa os temas nativos `Appearance / Light` e `Appearance / Dark`, sem fingir que o protótipo executa código React.
- Persistir somente `light` ou `dark` em `localStorage["hammerz:theme"]`. Valor ausente/inválido usa `light`. Se o armazenamento estiver bloqueado, a troca ainda funciona em memória sem interromper a aplicação. Aplicar a preferência antes da primeira pintura para evitar flash de tema incorreto. Login, logout, navegação e recarga não redefinem essa escolha.
- Um único mecanismo de tema controla a classe `dark` no elemento raiz, `color-scheme` e os tokens CSS compartilhados. A inicialização e o estado React devem permanecer sincronizados; não manter dois providers, duas chaves de preferência ou duas estratégias concorrentes de tema.
- Usar os mesmos componentes, rotas, validações, dados e layouts nos dois temas. Mudar somente os tokens semânticos de apresentação. Não duplicar páginas `*Dark`, componentes financeiros ou regras de negócio. Preservar cores naturais e proporções das imagens; não aplicar filtros de inversão às obras.
- Vincular superfícies, texto, bordas, botões, campos, foco e avisos a tokens semânticos. Separar o violeta de texto/foco da superfície de ação para preservar contraste; não usar o mesmo violeta claro como fundo de botão com texto branco no tema escuro. Estados de sucesso, erro e aviso mantêm texto/ícone explicativo, além da cor.
- Manter contraste mínimo de 4.5:1 para texto comum, 3:1 para texto grande e indicadores essenciais de controles/foco. Elementos desabilitados continuam legíveis e distinguíveis; não comunicar estado apenas por cor. Verificar formulários, loading, erros, cancelamento, finalização e os três resultados de auditoria nos dois temas.
- Não criar suporte genérico a múltiplas moedas: usar um formatter central com USD fixo. Preservar `currency: "USD"` nos contratos, constraints, ledger e evidência auditada, pois identifica a unidade financeira. Remover seletores antigos, handlers, opções, estado, flags, estilos, traduções e imports exclusivos de seleção de moeda; não deixar componentes escondidos ou código comentado. Não introduzir endpoint, `CurrencyProvider`, lista de moedas ou preferência financeira sem consumidor real.

| Token semântico | Light | Dark |
| --- | --- | --- |
| `color.bg` | `#F8F7F4` | `#15121C` |
| `color.surface` | `#FFFFFF` | `#211C2B` |
| `color.text` | `#25212E` | `#EDE9F5` |
| `color.muted` | `#706A7A` | `#B5ABBF` |
| `color.border` | `#E5E1EB` | `#493E58` |
| `color.controlBorder` | `#8A8097` | `#80718E` |
| `color.brand` (texto/foco) | `#6D43C5` | `#A277FF` |
| `color.action` (fundo de ação) | `#6D43C5` | `#7041BB` |
| `color.onAction` | `#FFFFFF` | `#FFFFFF` |
| `color.brandSoft` | `#F0EAFB` | `#2B223B` |
| `color.success` / `color.successSoft` | `#21664B` / `#E9F4EE` | `#82F7C4` / `#1D352F` |
| `color.danger` / `color.dangerSoft` | `#AD3547` / `#FCEEF0` | `#FF8FA8` / `#3C2532` |
| `color.warning` / `color.warningSoft` | `#895E18` / `#FCF3DF` | `#F4CD84` / `#3D3125` |

O Penpot mantém os mesmos nomes de tokens em dois conjuntos de cor mutuamente exclusivos e um conjunto comum de espaçamento. A implementação traduz esses nomes para variáveis CSS; os valores do design não criam uma segunda fonte de verdade para dados financeiros. O comportamento de tema não altera autenticação, operações pendentes, saldos ou auditoria.

## 5. Modelo de estados e invariantes

### 5.1 Estados do lote

Persistir `OPEN`, `CLOSED` ou `CANCELLED`. Derivar a apresentação com o horário do PostgreSQL:

| Condição | Estado exibido |
| --- | --- |
| `OPEN` e horário anterior a `starts_at` | `SCHEDULED` |
| `OPEN` e `starts_at <= db_now < ends_at` | `LIVE` |
| `OPEN` e `db_now >= ends_at` | `FINALIZING` |
| `CLOSED`, com ou sem vencedor | `CLOSED` |
| `CANCELLED` | `CANCELLED` |

Transições permitidas: criação → `OPEN`; `OPEN` → `CANCELLED` antes do fim; `OPEN` → `CLOSED` após o fim. Estados terminais não reabrem. Prorrogação altera `ends_at`, não o status persistido.

Na vitrine, a aba Encerrados inclui `FINALIZING` com indicação explícita de finalização, além dos `CLOSED`. Cancelados permanecem ocultos em todas as abas.

### 5.2 Criação e imutabilidade de configuração

- Leiloeiro seleciona um objeto real da API do museu. O servidor valida o ID e obtém os metadados; não confiar em título, imagem ou atributos enviados arbitrariamente pelo cliente.
- Exigir snapshot utilizável com título e imagem; atributos ausentes podem aparecer como “não informado”.
- `opening_bid_cents > 0`, `minimum_increment_cents > 0`, `starts_at < ends_at`, fim futuro e início não anterior ao horário do banco na criação.
- Todos os valores monetários são inteiros estritos, positivos quando aplicável e sujeitos aos limites da seção 5.3; rejeitar booleanos, frações e overflow.
- Não editar item, lance inicial, incremento ou início após publicação. O fim muda apenas pela regra anti-sniping. Correção de configuração exige cancelamento e novo lote.
- Assinar evento de criação com snapshot e regras para permitir detectar divergências posteriores nessas informações.

### 5.3 Carteiras e ledger

Carteiras existem para ambos os papéis: licitantes depositam e reservam; leiloeiros recebem liquidações. Não há saque ou transferência livre.

**Moeda única [DECISÃO]:** todo o sistema opera exclusivamente em USD (dólar americano), com duas casas decimais. Banco, ledger, lances, reservas, liquidações, eventos auditados e comprovantes usam a mesma unidade. Não existe escolha de moeda, conversão cambial ou suporte a múltiplas moedas neste MVP.

- Campos `*_cents` representam centavos de USD: `100000` corresponde a `$1,000.00`. Nunca usar float para cálculo financeiro; converter a entrada decimal validada para centavos inteiros.
- Respostas REST e snapshots WebSocket que contêm valores monetários incluem `currency: "USD"` no objeto financeiro correspondente. O servidor define a moeda; o cliente não pode escolher outra moeda. Não adicionar parâmetro de câmbio ou endpoint de conversão.
- Carteiras, lotes, ledger, settlements e recibos persistem `currency = 'USD'`, com valor padrão e constraint que rejeita outra moeda. Eventos canônicos de auditoria incluem a moeda; adulteração da moeda também deve ser detectada.
- Formatar valores com `Intl.NumberFormat("en-US", { style: "currency", currency: "USD" })`: `$1,500.00`, nunca separadores monetários brasileiros. Não adicionar um rótulo de USD isolado no cabeçalho nem qualquer seletor de moeda. Identificar `USD` somente no contexto financeiro necessário, especialmente rótulos de entrada e comprovantes públicos, para evitar ambiguidade do símbolo `$`.
- Limites e saldos iniciais abaixo são valores definidos em USD, não uma conversão de saldos em reais. Se uma implementação anterior já tiver dados em outra moeda, não relabelar nem converter saldos ou eventos silenciosamente; aplicar migração explícita ou usar um ambiente novo de avaliação, preservando o histórico anterior.

`available_cents = total_cents - committed_cents`

Invariantes no banco: `total_cents >= 0`, `committed_cents >= 0` e `committed_cents <= total_cents`. A reserva de um usuário soma os valores dos lotes `OPEN` em que ele é líder, inclusive os que aguardam liquidação.

Limites operacionais do MVP **[DECISÃO]**: até $100,000.00 USD por depósito; saldo total máximo de licitante de $1,000,000.00 USD; até 10 depósitos por minuto por usuário; lance inicial, incremento e lance individual no máximo $1,000,000.00 USD. Configurações devem usar centavos e constar no `.env.example`. Não impor o teto individual de licitante ao total recebido pelo leiloeiro; proteger overflow do `BIGINT` também nos créditos.

| Operação | Total | Comprometido |
| --- | --- | --- |
| Depósito simulado de `D` | `+D` | Inalterado |
| Novo líder com lance `B` | Inalterado | `+B` |
| Líder anterior superado, reserva `A` | Inalterado | `-A` |
| Cancelamento, reserva líder `B` | Inalterado | `-B` |
| Liquidação do vencedor por `B` | `-B` | `-B` |
| Crédito ao leiloeiro por `B` | `+B` | Inalterado |

Ledger registra `total_delta_cents` e `committed_delta_cents` separadamente, evitando ambiguidade entre dinheiro e reserva. Tipos: `OPENING_BALANCE`, `DEPOSIT_SIMULATED`, `BID_RESERVE`, `OUTBID_RELEASE`, `CANCELLATION_RELEASE`, `SETTLEMENT_DEBIT` e `SETTLEMENT_CREDIT`.

Cada operação registra seus movimentos na mesma transação dos saldos. Os deltas reconstroem os totais desde saldo inicial zero; o provisionamento inicial também usa movimentos explícitos `OPENING_BALANCE`, únicos por carteira e vinculados à operação de provisionamento. Esses créditos iniciais não são receita do leiloeiro nem depósitos disparados pelo login. Débito e crédito de uma liquidação devem somar zero no total. Falha antes do commit não altera saldos ou ledger. Linhas não são editadas/apagadas pela aplicação.

### 5.4 Aceitação de lance 

Aceitar somente se:

1. Usuário autenticado tem papel licitante.
2. Lote está `OPEN`, com `starts_at <= accepted_at < ends_at`.
3. Usuário não é o líder atual.
4. Primeiro lance é maior ou igual ao inicial; seguintes são maiores ou iguais a `current_bid_cents + minimum_increment_cents`.
5. Saldo disponível cobre o valor integral do novo lance, considerando reservas em outros lotes.
6. Histórico e evidência do lote estão coerentes e o diário externo está gravável e íntegro.

Obter `accepted_at` com `SELECT clock_timestamp()` depois de adquirir todos os locks necessários. Não usar `now()` capturado no início da transação nem timestamp enviado pelo cliente.

Na mesma transação: liberar integralmente a reserva do líder anterior, reservar o novo valor, gravar lance e movimentos, atualizar projeção do lote, aplicar eventual prorrogação e registrar evento de auditoria. Uma recusa não cria lance ou movimento financeiro.

### 5.5 Anti-sniping

Lance aceito nos últimos dois minutos prorroga o encerramento.

**[DECISÃO CONFIRMADA]** Se `0 < old_ends_at - accepted_at <= 120 segundos`, usar `new_ends_at = old_ends_at + 2 minutos`. Não usar `accepted_at + 2 minutos`.

Exemplo: fim às 15h e lance às 14h59min50s → novo fim às 15h02. Novos lances podem gerar novas extensões quando estiverem nos dois minutos finais do prazo vigente. Em `accepted_at == ends_at`, recusar. Um lance com extensão é uma única operação, um evento `BID_ACCEPTED` e um incremento da versão do lote; o evento inclui fim anterior e novo fim.

### 5.6 Cancelamento [EXTRA INCLUÍDO]

- Apenas o leiloeiro dono pode cancelar lote `OPEN` com `db_now < ends_at`, agendado ou ao vivo, com ou sem lances.
- Antes do primeiro lance, motivo é opcional: aceitar ausência, `null` ou texto vazio após trim; normalizar esses casos para `null`. Se preenchido, aceitar de 1 a 500 caracteres. Com qualquer lance no histórico, motivo público é obrigatório, após trim, entre 10 e 500 caracteres. Orientar a não incluir dados pessoais; tratar como texto simples, nunca HTML.
- Cancelamento com lances libera somente a reserva do líder atual. Reservas de lances superados já foram liberadas; reservas do usuário em outros lotes permanecem intactas.
- Não debitar vencedor, creditar vendedor ou gerar comprovante de arremate. É liberação de reserva, não estorno de pagamento liquidado. Sem lances, a UI mostra `No funds were reserved`, campo `Public cancellation reason (optional)` e a ação neutra `Keep auction`; não afirmar que uma reserva inexistente foi liberada. Sem motivo informado, sala e auditoria mostram `No reason provided`, junto de data/alias público, sem omitir o registro do cancelamento.
- Preservar lances, projeção do último lance e histórico; gravar `cancelled_at`, ator, motivo e evento `AUCTION_CANCELLED`, com referência à reserva liberada.
- Estado, liberação, ledger e evento são gravados na mesma transação. O cancelamento também participa do protocolo externo de auditoria.
- Lote vencido aguardando liquidação (`FINALIZING`) ou já encerrado não pode ser cancelado. Repetição idempotente de cancelamento confirmado retorna o resultado original.
- Publicar atualização após confirmação da operação; o cliente para o contador e mostra o motivo.
- Sem evidência externa disponível, recusar cancelamento antes do commit, mantendo a reserva. Não liberar dinheiro sem registrar a operação.

### 5.7 Encerramento e liquidação 

Tarefa periódica no backend, com intervalo inicial de 2 segundos, busca lotes `OPEN` vencidos. Ao iniciar/reiniciar o serviço, executar a mesma varredura. Intervalo é objetivo de atualização, não garantia de tempo real sob falha.

Dentro do protocolo transacional, bloquear lote; reler seu fim vigente e horário do banco. Se houve extensão ou cancelamento concorrente, reavaliar e não fechar indevidamente.

- **Com lances:** debitar total e reserva do vencedor; creditar total do leiloeiro; registrar ledger, settlement, recibo, `AUCTION_CLOSED` e `CLOSED`.
- **Sem lances:** fechar sem vencedor, transferência, settlement de arremate ou recibo; registrar `AUCTION_CLOSED` com resultado sem vencedor.
- `closed_at` representa o horário efetivo de liquidação; preservar também `ends_at` como prazo final.
- Settlement único por lote e recibo único por settlement; repetir o job não duplica transferências.
- Sem diário disponível ou diante de divergência, deixar `OPEN`/`FINALIZING`, sem aceitar novos lances e mantendo a reserva, até recuperação segura. Nunca fechar sem evidência e tentar corrigir depois.

## 6. Transações, idempotência e ordenação

### 6.1 Ordem de locks

**[DECISÃO]** Para tornar o protocolo de arquivo previsível no MVP de instância única, serializar as mutações de lotes auditados por uma trava global do diário. Ordem única: trava do diário → lote `FOR UPDATE` → carteiras em IDs crescentes. Criação não tem lote existente; obtém a trava antes de gravar o novo lote.

Usar mutex no processo e lock de arquivo exclusivo para impedir acesso acidental concorrente ao diário. Nenhum caminho adquire o diário depois de bloquear lote/carteiras. O fechamento, lance e cancelamento seguem a mesma ordem. Depósitos bloqueiam somente a carteira e não tentam obter diário/lote em seguida.

Transações PostgreSQL podem usar `READ COMMITTED` com essa disciplina e constraints. Não segurar locks enquanto consulta a API do museu; importar/validar catálogo antes da transação curta de criação. A serialização global limita throughput deliberadamente e é aceitável para a demonstração. Não adicionar workers sem redesenhar esse mecanismo.

### 6.2 Fluxo de lance

1. Validar autenticação e formato; consultar tentativa idempotente já conhecida.
2. Obter trava do diário e verificar se há pendência que impeça novas mutações auditadas.
3. Iniciar transação; obter lote e carteiras na ordem indicada; reconsultar idempotência.
4. Verificar coerência do histórico/projeções contra evidência independente; divergência bloqueia a mutação.
5. Ler `clock_timestamp()` após locks; validar janela, mínimo, liderança e saldo.
6. Preparar todas as alterações e o evento canônico; gravar pré-evidência externa durável conforme seção 7.
7. Persistir banco, ledger, resposta idempotente e incrementar `auction.version`; confirmar a transação.
8. Persistir confirmação externa durável e só então responder sucesso e publicar notificação.
9. Se houver resultado incerto após iniciar a gravação externa/commit, seguir recuperação da seção 7; não tratar como lance recusado comum.

Aceitação tem como referência o instante da validação após locks, anterior à persistência da evidência; não é o horário de recebimento HTTP ou de resposta. Definir timeouts curtos e limitados para não prender o lote indefinidamente. Se o timeout ocorrer antes da pré-evidência e do commit, rollback simples; depois, preservar o resultado como pendente até esclarecimento.

### 6.3 Chaves idempotentes

- `Idempotency-Key` UUID obrigatório em lances, depósitos e cancelamentos.
- Registro próprio com unicidade `(actor_id, idempotency_key)` e fingerprint incluindo método, rota/ID do recurso e payload normalizado.
- Mesma chave e mesmo payload retornam o resultado original confirmado, mesmo que o lote tenha fechado depois. Não recalcular resposta usando o estado atual.
- Em operações auditadas, encontrar a resposta no banco não basta para devolver sucesso: confirmar o `COMMIT` correspondente no diário. Sem decisão externa, responder pendência; diante de divergência, informar conflito de integridade.
- Mesma chave com payload diferente → `409 IDEMPOTENCY_KEY_REUSED`.
- Corrida em lotes diferentes com mesma chave também é resolvida pela constraint; rollback integral da tentativa perdedora, inclusive reservas. Não depender apenas do lock do lote.
- Persistir apenas operações que produziram efeito; erros de validação anteriores à preparação podem ser repetidos com a mesma chave. Pendências externas preservam `operation_id` e fingerprint; não reutilizar a chave em outra operação.
- Após perda de conexão ou `202 OPERATION_PENDING`, repetir com a mesma chave. A API não pode prometer que um `503` após commit significa ausência de efeito; distinguir indisponibilidade anterior ao efeito de resultado pendente.
- Chaves e respostas confirmadas são retidas durante todo o período de avaliação.
- Antes de enviar lance, depósito ou cancelamento, persistir no navegador somente os metadados necessários à tentativa: chave UUID, método/rota, payload normalizado, ID do ator autenticado, criação e `operation_id` se retornado. Usar um namespace próprio no localStorage para sobreviver a recarga/reabertura. Não gravar senha, JWT, dados de sessão, saldo autoritativo ou payloads de resposta privada nesse registro.
- Esses metadados são entrada não confiável: revalidar formato e usar autenticação/autorização normal em qualquer retry. Recuperar/reconciliar apenas tentativas do mesmo ator após `/auth/me`; nunca enviar uma operação da conta anterior com a sessão de outra pessoa. Não incluir essa persistência no cache privado de exibição que é limpo no logout.
- Repetir a requisição com a mesma chave e payload; a API retorna resultado original ou pendência. Remover a tentativa local apenas após resultado confirmado ou ausência de efeito conhecida pelo protocolo. Timeout, `202` ou perda de conexão não autorizam substituí-la por uma chave nova. Mostrar `Confirmation pending` enquanto não houver decisão.
- O registro do navegador não é fonte de verdade nem mecanismo de segurança; banco e diário continuam decidindo. A limpeza manual do armazenamento não desfaz operações. Documentar a limitação de recuperação automática quando a referência local for perdida; não inventar rollback pela ausência do registro local.

## 7. Auditoria e evidência independente

### 7.1 Garantia e modelo de ameaça

Auditar publicamente histórico e detectar inserção, alteração ou remoção posteriores, inclusive pelo acesso direto ao banco. **[DECISÃO]** Cobrir também criação, configuração inicial, cancelamento e fechamento do lote.

O adversário considerado pode editar/apagar/inserir linhas e projeções no PostgreSQL, inclusive apagar todo um lote. Ele não controla o processo da aplicação, o segredo HMAC, o filesystem do diário ou o host. Esse isolamento deve existir na instalação, não apenas na documentação: PostgreSQL sem volume de auditoria, sem segredo da API, sem superusuário do host ou acesso ao socket Docker. Acesso irrestrito ao servidor, comprometimento da aplicação ou destruição de todos os volumes estão fora da garantia. Não chamar a solução de imutabilidade absoluta ou backup contra perda do servidor.

A técnica escolhida é verificação server-side acessível sem login; HMAC não permite que visitantes validem assinaturas independentemente sem confiar no servidor. Não prometer prova criptográfica independente no navegador.

### 7.2 Eventos canônicos

Tipos: `AUCTION_CREATED`, `BID_ACCEPTED`, `AUCTION_CANCELLED`, `AUCTION_CLOSED`. `bid.sequence` conta somente lances; `audit_events.sequence` conta todos os eventos do lote. Nunca supor que sejam iguais.

Payload assinado inclui versão do schema, `deployment_id`, `operation_id`, lote, sequência, tipo, evento anterior, versões anterior/nova do lote, ator interno e alias público, horário, moeda `USD` e valores específicos da operação. No lance: ID e sequência do lance, licitante, valor, fim anterior/novo e deltas de reserva. Na criação: regras e snapshot. No cancelamento: motivo, ator, último lance e liberação. No fechamento: vencedor ou ausência dele, lance vencedor, valor, dados e IDs do settlement, snapshot público do recibo e movimentos financeiros relacionados com seus IDs, tipos, carteiras, horários e deltas. O campo do recibo que aponta para o hash do próprio evento é preenchido depois de calcular esse hash e excluído do payload assinado, evitando referência circular.

Não incluir senha, token ou e-mail. Identificadores internos usados na assinatura são removidos da representação pública, sem alegar que o payload redigido é idêntico ao assinado. A assinatura vincula o usuário interno para detectar troca de `bidder_id` mantendo o alias.

Canonicalização fixa: JSON UTF-8, chaves ordenadas, separadores compactos, sem floats, timestamps UTC em formato único com microssegundos, UUIDs normalizados e strings preservadas. Hash de evento: HMAC-SHA256 sobre domínio de assinatura versionado e payload canônico contendo o hash anterior; comparar em tempo constante. Definir gênese por lote e chave de identificação de segredo. Manter segredo estável fora do banco; não trocar silenciosamente em redeploy.

### 7.3 Diário persistente externo

- Arquivo JSONL em `audit_data`, fora do diretório PostgreSQL, com escrita append-only pela aplicação e permissões restritas ao usuário do backend.
- Manifesto inicial assinado com `deployment_id`, versão e gênese; persistir arquivo e diretório na criação. Não criar diário vazio automaticamente se há banco ou implantação já existente.
- Cada registro tem sequência global, hash anterior, tipo `PREPARE`, `COMMIT` ou `ABORT`, `operation_id`, referência ao evento e HMAC próprio. `PREPARE` preserva o evento completo, contexto e fingerprint necessários à comparação posterior.
- Uma única operação auditada em preparação por vez no MVP. Cada append exige escrita completa, flush e `fsync` antes de avançar. Validar a cadeia ao abrir e manter a posição confirmada em memória enquanto o arquivo estiver sob controle exclusivo.
- Nunca reescrever, truncar, “corrigir” ou substituir evidência automaticamente com base em dados do PostgreSQL. Não usar apenas arquivo dentro do container descartável nem `audit_head` na mesma tabela do lote como âncora independente.
- Corrupção, bytes finais incompletos, erro de disco, troca de identidade ou arquivo ausente deixam a auditoria indisponível; preservar bytes e interromper mutações auditadas até recuperação explícita.

### 7.4 Protocolo de confirmação

1. Sob locks e após validação, gerar `operation_id`, evento e alterações previstas.
2. Acrescentar `PREPARE` assinado ao diário e executar sincronização durável **antes do commit PostgreSQL**. Se não for possível iniciar a evidência com segurança, rollback e `503 AUDIT_UNAVAILABLE`, sem efeito financeiro.
3. Gravar o evento e todos os efeitos na mesma transação PostgreSQL, incluindo resposta idempotente.
4. Se o commit for confirmado, acrescentar `COMMIT` ao diário e sincronizar. Somente depois responder sucesso/publicar WebSocket.
5. Se o rollback for inequivocamente confirmado, acrescentar `ABORT` assinado e sincronizar antes de permitir a próxima mutação auditada. Isso só é permitido enquanto o processo conhece o resultado, nunca por inferência de uma linha ausente após restart.
6. Se a conexão cair durante o commit ou a gravação da confirmação externa falhar, preservar a intenção, bloquear novas mutações auditadas e retornar `202 OPERATION_PENDING` quando for possível responder. Não executar compensação nem devolver reserva automaticamente: o banco pode ter confirmado.

O protocolo não torna arquivo e banco uma transação atômica. Ele mantém evidência anterior e torna incertezas visíveis. Na transição, o verificador retorna `UNVERIFIABLE`; nunca `VERIFIED` por encontrar uma cadeia curta válida no banco.

### 7.5 Recuperação e intenções órfãs

Na inicialização, validar manifesto/cadeia completa antes de liberar mutações auditadas. Para operações com `COMMIT` externo, comparar conteúdo e efeitos no banco: ausência, diferença ou ordem incorreta é adulteração. Para `ABORT`, os efeitos não podem existir. Eventos no banco sem preparação/commit externo válido também são divergência, exceto intenção ainda explicitamente pendente.

**Uma intenção `PREPARE` sem decisão durável após reinício permanece pendente.** A ausência de linhas no banco não prova rollback: pode ser uma exclusão posterior. A presença de linhas também não substitui a confirmação independente. Não gerar `ABORT`/`COMMIT` automaticamente confiando apenas no banco potencialmente adulterado.

Neste MVP, resolver esse caso exige procedimento administrativo explícito: preservar evidência e dump, examinar logs/backup independentes e restaurar um par coerente se disponível. Sem evidência suficiente, manter a pendência e o bloqueio; não declarar o histórico íntegro. Essa escolha prioriza integridade sobre recuperação automática e dispensa coordenação distribuída complexa no prazo do teste. O README deve demonstrar o comportamento de crash e a limitação de disponibilidade; uma pendência não é uma implementação aceitável para o fluxo saudável de demonstração.

Bloqueio global de novas mutações auditadas é intencional enquanto o diário estiver incerto; depósitos e consultas podem continuar se o banco estiver disponível. Fechamentos aguardam com reservas preservadas. Não apagar o lote/diário para desbloquear a demonstração.

### 7.6 Verificação pública

Verificar sob a mesma trava do diário e com snapshot consistente do banco, evitando comparar uma metade de operação em andamento. Limitar tempo de espera; indisponibilidade de prova retorna explicitamente `UNVERIFIABLE`. Calcular resultado em consulta, não servir um selo antigo de integridade em cache após possível edição direta no banco.

Comparações obrigatórias:

- Manifesto, sequências, HMACs e encadeamento global e por lote.
- Todos os `BID_ACCEPTED` confirmados externamente versus `bids` e `audit_events`, incluindo IDs internos, ordem, valores e horários.
- Criação versus configuração/snapshot persistidos; eventos de lance versus prorrogações e projeção do último líder/valor.
- Cancelamento versus status, motivo e movimento de liberação; fechamento versus status, settlement, recibo e movimentos financeiros vinculados.
- Ausência de eventos/linhas extras, repetidos, apagados ou sem evidência correspondente. Excluir o último lance, todos os lances ou o lote inteiro deve ser detectado com a evidência externa preservada.

As carteiras variam também por outros lotes e depósitos; não comparar o saldo atual com um saldo antigo de um evento isolado. Reconciliar ledger e reservas de forma agregada nos testes internos. A auditoria pública de um lote não expõe carteiras ou movimentos de outras pessoas.

| Resultado | Significado |
| --- | --- |
| `VERIFIED` | Evidência válida, operações decididas e todas as comparações do lote coerentes |
| `TAMPERED` | Divergência comprovada com evidência válida; informar código de motivo |
| `UNVERIFIABLE` | Evidência inacessível/corrompida ou operação incerta; não afirmar integridade |

Se houver divergência comprovada e também pendência, retornar `TAMPERED` com detalhes das incertezas adicionais. Resposta inclui `reason_codes`, `checked_at`, última sequência confirmada e head quando disponíveis. Lote presente no diário e apagado no banco recebe resultado de adulteração no endpoint de auditoria, não um simples “não encontrado”. Ausente de ambos recebe `404`.

Mostrar histórico com aliases estáveis por lote, nunca e-mail, nome, login, IDs de carteira ou IDs internos de usuário. A identidade pública do vendedor também é alias. Histórico adulterado deve ser rotulado; quando disponível, distinguir a evidência confirmada externa da representação divergente do banco, sem corrigir o banco silenciosamente.

O endpoint público de lances segue a mesma regra: não servir linhas divergentes como histórico íntegro. O comprovante inclui o resultado atual da auditoria; se houver adulteração ou pendência, exibir o alerta e não apresentar o documento como arremate validado.

## 8. Dados e constraints

| Tabela | Campos principais e regras |
| --- | --- |
| `users` | UUID, e-mail normalizado único, hash da senha, papel `SELLER/BIDDER`, criação |
| `wallets` | Usuário único/FK, total, comprometido, atualização; constraints dos saldos |
| `catalog_items` | Provider, ID externo, título, artista, descrição, imagem e metadados; snapshot local imutável |
| `auctions` | Vendedor, item, status, versão, lance inicial, incremento, líder/valor atuais opcionais, início/fim, cancelamento/motivo e fechamento |
| `bids` | UUID, lote, licitante, valor, horário aceito, sequência de lance, operação |
| `audit_events` | UUID, lote, sequência de evento, tipo, operação, lance opcional, payload canônico, hash anterior e hash do evento |
| `wallet_ledger` | UUID, carteira, operação, lote/settlement opcionais, tipo, delta total, delta comprometido, data |
| `idempotency_requests` | Ator, chave UUID, fingerprint, operação, HTTP status e resposta persistida |
| `settlements` | UUID, lote único, vencedor, lance vencedor, valor e horário; apenas arremates com vencedor |
| `receipts` | UUID público não sequencial, settlement único, snapshot público, data e hash do evento de fechamento |

`operation_id` identifica uma operação de negócio e é compartilhado pelas suas linhas. O estado externo PREPARE/COMMIT/ABORT pertence ao diário; um campo do banco não o substitui.

Constraints mínimas:

- FKs com `ON DELETE RESTRICT` onde apagar histórico por cascata seria indevido.
- `UNIQUE(auction_id, sequence)` separado em `bids` e `audit_events`.
- `UNIQUE(actor_id, idempotency_key)` em `idempotency_requests`.
- `UNIQUE(operation_id, wallet_id, type)` no ledger para impedir duplicação de movimentos de mesma natureza.
- Um settlement por lote, recibo por settlement e evento por operação auditada.
- Lance inicial/incremento/valor positivos; datas coerentes; status/role/tipos válidos; saldos válidos.
- Líder e lance atual ambos nulos antes de haver lance, ambos presentes depois. Cancelamento preserva o último líder como histórico, mas não uma reserva ativa.
- Papel do ator, reservas entre tabelas e relação do vencedor com o último lance exigem validação transacional além de constraints locais.

Índices: status/fim do lote; vendedor/data de criação; licitante/data do lance; lote/sequência de lance; lote/sequência de evento; carteira/data do ledger; operação nas tabelas relacionadas. Não usar sequência global automática do banco como substituto da sequência lógica do histórico por lote.

## 9. API REST v1

| Método | Caminho | Acesso | Função |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/register` | Público | Cadastrar licitante e carteira zero |
| POST | `/api/v1/auth/login` | Público | Autenticar |
| GET | `/api/v1/auth/me` | Autenticado | Perfil e papel |
| GET | `/api/v1/catalog/search?q=&offset=&limit=` | Leiloeiro | Buscar objetos externos |
| POST | `/api/v1/auctions` | Leiloeiro | Criar lote com snapshot validado |
| GET | `/api/v1/auctions?status=&offset=&limit=` | Público | Vitrine paginada |
| GET | `/api/v1/auctions/{id}` | Público | Estado atual e horário do servidor |
| POST | `/api/v1/auctions/{id}/bids` | Licitante | Lance idempotente |
| POST | `/api/v1/auctions/{id}/cancel` | Dono | Cancelamento idempotente e motivo |
| GET | `/api/v1/auctions/{id}/bids?before_sequence=&limit=` | Público | Histórico pseudonimizado, paginado sem omitir acesso ao restante |
| GET | `/api/v1/auctions/{id}/audit?before_sequence=&limit=` | Público | Resultado da verificação completa e página de eventos públicos |
| GET | `/api/v1/seller/auctions` | Leiloeiro | Gestão própria, resultados e total recebido |
| GET | `/api/v1/me/auctions/{id}/status` | Licitante | Posição privada e resultado próprio |
| GET | `/api/v1/wallet` | Licitante | Total, comprometido e disponível |
| POST | `/api/v1/wallet/deposits` | Licitante | Depósito fictício idempotente |
| GET | `/api/v1/me/bids-and-wins` | Licitante | Participações, vitórias e cancelamentos |
| GET | `/api/v1/receipts/{id}` | Público | Comprovante |
| GET | `/health/live` | Público | Processo ativo |
| GET | `/health/ready` | Público | Banco e diário prontos para mutações auditadas |

### 9.1 Filtros e paginação

- Vitrine: `GET /api/v1/auctions?status=LIVE&offset=0&limit=20`. `status` aceita somente `SCHEDULED`, `LIVE` ou `ENDED`; padrão `LIVE`. `SCHEDULED` = OPEN antes de starts_at; `LIVE` = OPEN dentro da janela; `ENDED` = CLOSED ou OPEN com prazo vencido (FINALIZING). CANCELLED nunca é retornado nessa coleção. Não interpretar `OPEN` persistido como sinônimo de `LIVE`.
- Painel: `GET /api/v1/seller/auctions?status=ALL&offset=0&limit=20`; filtro aceita `ALL`, `SCHEDULED`, `LIVE`, `ENDED`, `CANCELLED`; sempre restringir ao vendedor autenticado.
- Participações: `GET /api/v1/me/bids-and-wins?tab=ACTIVE&offset=0&limit=20`; `tab` aceita `ACTIVE`, `WON`, `PAST`, conforme seção 4.4. As contagens de abas são calculadas antes de aplicar a paginação, sem incluir lotes em que o usuário não participou.
- Paginação por offset: inteiro >= 0, limite de 1 a 50, padrão 20; exceção: busca no catálogo limita `limit` a 1–20, conforme seção 11. Envelope: `items`, `total`, `offset`, `limit`, `has_more`; informar contagens por situação quando a UI as exibir. Rejeitar enum/limite inválido com 422.
- Histórico e auditoria retornam as entradas mais recentes primeiro por padrão, com `limit` e `before_sequence` exclusivo para buscar anteriores. Para reconciliação de novidades, aceitar `after_sequence` exclusivo e ordenar esse resultado em sequência crescente. Não combinar os dois cursores na mesma requisição. A resposta informa `items`, `next_before_sequence` e `has_more`; não permitir lacunas/duplicatas na coleção acumulada. Auditar sempre o lote inteiro antes de paginar sua apresentação. `Load earlier bids` acessa todas as entradas anteriores, sem limitar o histórico aos exemplos visíveis.

### 9.2 Payloads e respostas

Lance e depósito recebem `amount_cents`; cancelamento recebe `reason`. Criação recebe somente ID externo do item, valores e horários necessários; o vendedor deriva da sessão. Erros têm `code`, `message`, `details?` e `request_id`, sem stack trace ou segredos.

| HTTP | Uso |
| --- | --- |
| 200/201 | Consulta ou mutação confirmada; retry retorna o resultado original |
| 202 | `OPERATION_PENDING`, resultado ainda não confirmado no diário; inclui `operation_id` e orientação de retry com mesma chave |
| 401/403 | Falta de autenticação ou permissão |
| 404 | Recurso inexistente; observar exceção de lote apagado conhecido pelo diário |
| 409 | Conflito de negócio, saldo insuficiente, liderança própria, lote inelegível, chave reutilizada ou integridade divergente |
| 422 | Payload, motivo ou valores inválidos |
| 429 | Limite de requisições |
| 503 | Dependência indisponível antes de confirmar efeito; diferenciar catálogo, banco e auditoria |

Snapshot público e eventos incluem `version`, `server_time`, situação persistida/derivada, prazos e aliases públicos; sem IDs de usuários. O painel soma créditos efetivamente liquidados dos lotes próprios; não soma reservas ou lotes em finalização como receita.

## 10. WebSocket e reconciliação

Conexão pública em `/ws/auctions/{auction_id}`, somente para acompanhamento. Lances continuam via REST autenticado. Validar origem e limitar conexões; não transportar JWT na URL pública.

Tipos canônicos: `auction.snapshot`, `bid.accepted`, `auction.cancelled`, `auction.closed`. Erros de conexão seguem contrato próprio; não usar evento público para transportar falha privada de lance.

- Criação inicia `auction.version = 1`; cada lance, cancelamento ou fechamento confirmado incrementa uma vez.
- Um lance prorrogado gera **um único `bid.accepted`**, contendo a alteração completa e `extended=true`, `previous_ends_at` e `ends_at`. Não emitir segundo evento dependente com a mesma versão.
- Cada mensagem contém ID do evento, lote, tipo, versão, horário do servidor e snapshot público suficiente para aplicar aquela transição. Lance inclui sequência de lance; evento de auditoria tem sequência própria.
- Assinar a sala antes de obter o snapshot inicial, com buffer/ordenação no cliente, para não perder alteração entre GET e subscription. Aplicar snapshot e eventos pela versão.
- Evento com versão menor/igual é ignorado; lacuna de versão dispara REST e atualização do histórico. Mesmo evento completo pode exigir refetch do histórico para buscar entradas intermediárias.
- Ao reconectar ou recuperar foco, consultar snapshot e posição privada. Reconexão tem backoff limitado.
- Enquanto sala estiver aberta, refetch de snapshot a cada 5 segundos para recuperar inclusive o último evento perdido, sem precisar de evento posterior para revelar lacuna. Pode reduzir frequência em lotes terminais.
- Toda alteração relevante invalida posição privada do usuário e carteira, mesmo quando outro licitante deu o lance. Na página da carteira, refetch periódico e no foco preserva atualização entre lotes.
- Falha de broadcast depois de uma operação confirmada não desfaz lance ou liquidação. Publicar somente depois de COMMIT PostgreSQL e confirmação externa; durante pendência, REST pode mostrar dados já persistidos com `confirmation_pending=true` e auditoria não verificável.
- Indicadores de vitória definitiva e links de comprovante só aparecem como confirmados quando a operação de fechamento tiver evidência externa concluída.

## 11. Catálogo externo e tolerância a falhas

API selecionada: Metropolitan Museum of Art Collection API.

- Busca: `GET https://collectionapi.metmuseum.org/public/collection/v1.1/search?q=...&hasImages=true&offset=0&limit=20`.
- Detalhes: `GET https://collectionapi.metmuseum.org/public/collection/v1/objects/{object_id}`.
- Busca retorna IDs; obter detalhes com concorrência limitada a 4 chamadas, timeout de 5 segundos por chamada e no máximo 2 retries com backoff para falhas transitórias. Limitar página da aplicação a 20 resultados, tratando páginas parciais.
- Preferir itens em domínio público (`isPublicDomain=true`) com imagem utilizável. Informar origem e link do museu; obras são usadas em demonstração de leilão simulado, sem afirmar propriedade real.
- Não carregar todos os detalhes do acervo nem buscar a API em cada leitura de lote. Cache curto de busca pode ser em memória, pois não é fonte de verdade.
- Snapshot local guarda título, artista, atributos, descrição, imagem de referência e metadados necessários. Sem imagem remota disponível, mostrar placeholder local e preservar os dados e fluxos.
- Não aceitar URLs arbitrárias para fetch no backend: base do provider é fixa e ID validado. Se futuramente houver download de imagem, validar host/tamanho/content-type para evitar SSRF; não é exigido neste MVP.
- API externa fora do ar afeta busca/importação de novos itens, com mensagem e opção de tentar novamente; não derruba autenticação, carteira, lotes existentes, sala, auditoria ou recibos.

## 12. Segurança, operação e observabilidade

- HTTPS/WSS; banco e backend sem publicação direta de portas em produção. Caddy é a entrada pública.
- Mesmo origin em produção; CORS explícito apenas para origens locais de desenvolvimento quando necessário. Nunca combinar credenciais com origem curinga.
- Segredos separados para JWT, HMAC de evidência e aliases; `.env` ignorado e `.env.example` sem valores reais. Não usar credenciais públicas de avaliação como segredo operacional.
- Aliases estáveis por lote derivados de segredo e identidade; não usar e-mail truncado ou nome real como pseudônimo.
- Rotas públicas usam schemas explícitos; nunca serializar modelos ORM completos de usuários, carteiras ou eventos internos.
- Rate limiting simples em memória é suficiente sob instância única; não usar esse limite como regra financeira ou proteção de integridade.
- Operações síncronas de arquivo, hashing ou Argon2 não podem bloquear o event loop prolongadamente; usar execução apropriada mantendo disciplina de locks.
- Logs estruturados com request/operation/auction IDs; sem senha, token, e-mail, payload privado ou segredo. Registrar falhas de encerramento e de diário.
- Readiness pode falhar durante indisponibilidade do diário sem desligar o processo que serve consultas. Não reiniciar a aplicação em loop apenas por readiness falsa.
- Migrations executadas antes da API; aguardar PostgreSQL saudável, aplicar Alembic e iniciar um worker. Seed é comando explícito, idempotente, sem reset destrutivo no startup.
- Backup inclui banco, diário, manifesto e segredos de verificação. Para checkpoint coerente, pausar mutações financeiras e auditadas, esperar operações em voo e capturar o conjunto; testar restauração em ambiente separado.
- Não restaurar banco antigo com diário novo apagando evidência para fazê-los concordar. Backups anteriores à adulteração podem fundamentar recuperação administrativa documentada; restaurar não apaga o registro do incidente.
- Reinícios comuns com diário totalmente decidido retomam lotes vencidos sem duplicidade. Perda de host/disco e failover automático estão fora do MVP.

## 13. Contas e dados iniciais de avaliação

Publicar pelo menos um leiloeiro, dois clientes e um lote com lances abertos.

**[DECISÃO]** As contas são persistentes e usam login convencional. Credenciais ficam no README. Os saldos abaixo são os saldos correntes após preparar os lotes de avaliação, não créditos concedidos pelo login.

### 13.1 Contas e reconciliação inicial

| Conta | Papel | Crédito inicial no ledger | Total após preparar os lotes | Comprometido | Disponível |
| --- | --- | --- | --- | --- | --- |
| `seller@hammerz.test` | SELLER | $0.00 | $2,400.00 | $0.00 | $2,400.00 contabilmente; sem carteira de licitante |
| `bidder1@hammerz.test` | BIDDER | $12,400.00 | $10,000.00 | $1,500.00 | $8,500.00 |
| `bidder2@hammerz.test` | BIDDER | $10,000.00 | $10,000.00 | $1,500.00 | $8,500.00 |

Todos os valores são USD. O licitante 1 venceu o lote 003 por $2,400.00: 12,400 − 2,400 = 10,000. O vendedor começou em zero e recebeu essa liquidação. O licitante 1 lidera o lote 002; o licitante 2 lidera o lote 001. Cada um tem $1,500.00 reservados. O cancelado 005 não mantém reserva.

- Endereços `.test` são identificadores de autenticação sem entrega de e-mail. Senhas de avaliação ficam no README e são armazenadas com Argon2; não reutilizá-las em outros sistemas.
- Créditos iniciais são movimentos explícitos `OPENING_BALANCE` de 1.240.000 e 1.000.000 centavos, únicos por carteira. Não criar crédito inicial para novos cadastros públicos. O vendedor não recebe crédito inicial.
- O seed executa os serviços de domínio para preparar histórico, liberação de reservas e liquidação; não insere lances ou saldos finais diretamente para reproduzir o quadro.
- Valores e posições mudam normalmente durante avaliação; nunca restaurar esse quadro por login, logout, refresh, deploy ou reinício.

### 13.2 Conjunto de lotes coerente com a UI

Os números são referências de apresentação. Gerar e persistir UUIDs reais e manter o mapeamento no seed, sem usar título como identidade. Os aliases abaixo são fixtures do design; em execução, derivá-los do segredo e usuário/lote conforme a política de privacidade, mantendo consistência entre sala, auditoria e recibo.

| Lote | Obra / Met objectID | Situação | Lance inicial / incremento | Resultado ou lance atual |
| --- | --- | --- | --- | --- |
| 001 | Wheat Field with Cypresses / 436535 | Live | $950.00 / $50.00 | 12 lances; $1,500.00, licitante 2 lidera; licitante 1 foi superado em $1,450.00 |
| 002 | Self-Portrait with a Straw Hat / 436532 | Live | $1,450.00 / $50.00 | 2 lances; licitante 1 lidera com $1,500.00 |
| 003 | Self-Portrait with a Straw Hat / 436532 | Ended / settled | $2,300.00 / $50.00 | 3 lances; licitante 1 venceu por $2,400.00; recibo público correspondente |
| 004 | Wheat Field with Cypresses / 436535 | Upcoming | $1,000.00 / $50.00 | Sem lances; início futuro |
| 005 | Wheat Field with Cypresses / 436535 | Cancelled | $1,000.00 / $50.00 | 3 lances, último $1,100.00 do licitante 2; licitante 1 participou com $1,050.00; reserva liberada |

- Lote 001: valores 950, 1000, …, 1500, com incremento de 50 e alternância entre os dois licitantes, começando no licitante 1. Assim, 12 lances terminam em 1500. Um novo lance do licitante 1 de 1550 é a sequência 13; ele passa a ter 3050 comprometidos entre lotes 001 e 002 e 6950 disponíveis.
- Lote 002: licitante 2 oferece 1450 e licitante 1 oferece 1500; a reserva anterior é liberada.
- Lote 003: lances 2300 do licitante 1, 2350 do licitante 2 e 2400 do licitante 1; fechar e liquidar normalmente para produzir o recibo e o total recebido de 2400.
- Lote 005: 1000 do licitante 2, 1050 do licitante 1 e 1100 do licitante 2; cancelar antes do fim com motivo `The artwork is no longer available for this auction.`. Só a reserva final de 1100 é liberada no cancelamento.
- Obras repetidas pertencem a lotes de avaliação distintos, com IDs e históricos próprios. Não se afirma propriedade ou venda real de bens do museu.
- Abas iniciais do licitante 1: Active bids = 2 (001 e 002), Won = 1 (003), Past auctions = 1 (005). Vitrine: Live = 2, Upcoming = 1, Ended = 1; lote 005 omitido. Painel do vendedor inclui os cinco lotes e total recebido de 2400.
- Outro ramo ilustrado no Penpot: adicionar 1000 à carteira base resulta em total 11000, comprometido 1500 e disponível 9500. Se depois liderar também o lote 001 por 1550, disponível = 7950. Não somar operações de ramos independentes do protótipo por engano.

### 13.3 Provisionamento e disponibilidade

- `seed-demo` é comando explícito e idempotente: cria somente dados ausentes e não redefine senha, saldo, reservas, horários ou histórico já existentes. Identificar as operações por chaves próprias e garantir unicidade no banco.
- Horários de 25–27/10/2026 no design são ilustrativos. O seed usa o relógio do banco e constrói datas relativas à execução para que 001/002 estejam efetivamente ao vivo, 004 no futuro e 003/005 terminais.
- Para preparar históricos terminais sem esperar horas, um seed pode criar lotes com início imediato e janela maior que dois minutos, executar os lances antes dos dois minutos finais quando não se deseja extensão e aguardar o encerramento real. Não mudar relógio, retroagir `accepted_at`, contornar anti-sniping ou forçar settlement por inserts. Uma alternativa documentada é um conjunto inicial previamente preparado pelos mesmos serviços antes da entrega. Planejar essas janelas no início da implantação, não nos últimos minutos.
- `seed-demo --ensure-live` cria novo lote quando não houver lote de avaliação efetivamente ao vivo, usando snapshot importado se necessário. Não reabre lotes, concede créditos, apaga histórico ou altera fim silenciosamente. Não precisa recriar as cinco fixtures em cada execução.
- Executar ensure-live e verificar disponibilidade antes da submissão. Se os saldos forem consumidos durante avaliação, `Add funds` continua disponível pelo fluxo normal.
- Não oferecer reset público, troca de papel ou execução de seed pelo navegador. Documentar comandos, credenciais, origem das obras e roteiro de duas sessões no README.

## 14. Testes e validação

Usar pytest com PostgreSQL real para regras transacionais e concorrência, além de diretório temporário de diário para testes de integração. SQLite não substitui os testes de locks. Usar testes focados nos resultados de negócio e nas falhas relevantes, sem perseguir cobertura percentual artificial.

### 14.1 Autenticação e autorização

- Cadastro cria somente licitante e carteira zero; exige login antes de abrir a carteira. E-mail duplicado sob concorrência não cria duas contas.
- Leiloeiro não dá lances ou deposita; licitante não cria/cancela lote; um vendedor não gerencia lote de outro.
- Token expirado e tentativa de forjar role/IDs são rejeitados; páginas públicas não vazam dados pessoais.

### 14.2 Lances e saldo

- Primeiro lance igual ao inicial aceito; abaixo rejeitado; seguintes respeitam incremento.
- Líder não cobre o próprio lance; fora da janela ou cancelado não aceita lance.
- Saldo insuficiente não altera banco/ledger; reserva do líder anterior libera integralmente quando superado.
- Um usuário liderando dois lotes não reserva mais que seu total; disputa concorrente em lotes diferentes considera a mesma carteira.
- Dois lances concorrentes preservam um líder, ordem de histórico e saldos válidos.
- Requisição esperando lock até após o fim é recusada; accepted_at vem do relógio pós-lock.
- Idempotência cobre retry, chave com payload diferente, perda de resposta e corrida entre lotes diferentes.
- Depósitos respeitam limites e não duplicam sob retry.
- Toda quantia usa centavos inteiros de USD; REST/WS informam a moeda, formatação usa `en-US` e valores em outra moeda são rejeitados.
- Executar `seed-demo` novamente, fazer login e reiniciar a aplicação não duplica créditos iniciais nem restaura saldo/reservas.
- As duas contas provisionadas usam autenticação convencional; não existe login especial ou seletor de conta na UI.

### 14.3 Prazo, cancelamento e liquidação

- Anti-sniping soma exatamente 2 minutos ao fim anterior, inclusive no limite de 120 segundos; no horário final o lance é recusado.
- Cancelamento sem lance funciona com motivo ausente/vazio e não cria liberação de reserva inexistente. Com lance exige motivo de 10–500 caracteres e libera apenas a reserva desse lote.
- Motivo inválido, outro vendedor ou lote em finalização/encerrado não cancela.
- Retry de cancelamento não libera duas vezes; histórico e motivo continuam acessíveis publicamente sem PII.
- Corridas lance/cancelamento e fechamento/extensão/cancelamento têm um resultado serial válido, sem duplo efeito.
- Encerramento sem lance fecha sem recibo; com vencedor transfere uma vez, credita o vendedor e concilia ledger.
- Reexecução/restart não duplica settlement ou recibo; expirado ainda OPEN mostra FINALIZING.

### 14.4 Adulteração e falhas de auditoria

- UPDATE, INSERT e DELETE em `bids` e `audit_events`, em evento intermediário/último/todos, resultam em divergência quando a evidência está disponível.
- Troca de licitante, valor, timestamp ou sequência, replay de outro lote e alteração da projeção também são detectados.
- Alteração de regras iniciais, motivo/status de cancelamento, settlement, movimento vinculado ou snapshot do recibo diverge do evento confirmado.
- Apagar o lote inteiro continua detectável pelo diário; endpoint público não oculta o caso como simples 404.
- Diário ausente, corrompido, sem permissão ou com disco cheio não gera VERIFIED e bloqueia novos lances sem efeito financeiro se a preparação não ocorreu.
- Injetar falhas antes/depois de PREPARE, durante commit e antes/depois do COMMIT externo; verificar rollback conhecido, confirmação pendente e ausência de aborto inferido pela falta de linha.
- PREPARE órfão após restart preserva evidência, bloqueia mutações auditadas e permanece UNVERIFIABLE; COMMIT confirmado com evento apagado resulta TAMPERED.
- Auditoria concorrente com lance não produz falso positivo por leitura de estado intermediário.

### 14.5 Interface e entrega

- Build TypeScript/Vite e lint/testes backend no CI.
- Duas sessões autenticadas disputam o mesmo lote sem refresh; ganhando/superado e carteira atualizam.
- Perda do último evento WS, reconexão e mudança de foco recuperam estado por REST; evento com extensão não perde o novo fim.
- Retorno após depósito mantém o saldo novo; lance confirmado atualiza líder e histórico com a mesma sequência, sem dados antigos.
- Cadastro, login por papel, navegação de visitante, abas de catálogo/participações, busca, paginação de histórico e compartilhamento são exercitados em desktop e mobile.
- Recibo e auditoria preservam o lote escolhido; a auditoria de cancelado mantém todos os lances; recibos mostram a situação atual de integridade.
- Retry após recarga e reautenticação usa a chave original; trocar de conta não reenvia tentativa de outro usuário.
- Imagens preservam proporção e recibo mobile mantém horário/fuso e dados obrigatórios.
- Lote cancelado some da vitrine e exibe motivo por URL direta; posição dos participantes atualiza.
- Desligar acesso ao catálogo não quebra os quatro fluxos exigidos: vitrine, sala, auditoria e comprovante.
- Tema: alternar por mouse/teclado em desktop/mobile, navegar, recarregar, fazer logout e abrir documento público preservando a escolha. Validar primeira pintura, preferência inválida e storage bloqueado. Conferir contraste, foco, formulários/avisos e imagens naturais nos dois temas.
- USD permanece fixo; não existe seletor nem resíduo de seleção de moeda em componentes, handlers, estado, estilos ou imports.
- Testar HTTPS, WSS, login, depósito, lance, cancelamento e compartilhamento sem login no deploy público, por rede externa. Verificar `/health/live` e `/health/ready` através do Caddy: retornam HTTP/JSON do backend, inclusive 503 quando aplicável, em vez do fallback HTML da SPA.

## 15. Organização do código

Monorepo com responsabilidades explícitas, sem necessidade de múltiplas camadas abstratas para operações simples.

| Caminho | Responsabilidade |
| --- | --- |
| `frontend/src/app` | Rotas, providers e sessão |
| `frontend/src/pages` | Telas |
| `frontend/src/features` | Auth, catálogo, lotes, carteira e auditoria |
| `frontend/src/components` | Componentes compartilhados |
| `frontend/src/lib` | Cliente HTTP, WS e formatação |
| `backend/app/api` | Rotas e contratos de entrada/saída |
| `backend/app/core` | Configuração, auth e erros |
| `backend/app/db` | Conexão, sessão e modelos |
| `backend/app/modules` | Serviços de auth, catálogo, lotes, carteira, liquidação e auditoria |
| `backend/app/realtime` | Broadcast e gerenciamento de conexões |
| `backend/migrations` | Alembic |
| `backend/tests` | Testes de domínio e integração |
| `infra/Caddyfile` | SPA, proxy e HTTPS |
| `compose.yaml` | Execução local/servidor com volumes e healthchecks |
| `.github/workflows/ci.yml` | Lint, testes com PostgreSQL e build |
| `.env.example` | Configurações e placeholders |
| `README.md` | Execução, arquitetura, decisões, testes e entrega |
| `SPEC.md` | Esta especificação incorporada ao repositório |

## 16. Plano para o prazo restante

| Etapa | Entrega |
| --- | --- |
| Dia 1 | Compose, migrations, auth/cadastro, diário e teste inicial de falhas; primeiro deploy HTTPS; catálogo e criação/vitrine básica |
| Dia 2 | Carteira, lances, locks, idempotência, anti-sniping e cancelamento com motivo; testes financeiros e de adulteração |
| Dia 3 | Encerramento/recibo, WebSocket e reconciliação; todas as telas; seed e smoke público |
| Dia 4, se disponível | Corrigir falhas, testar crash/concorrência, revisar README e executar roteiro de entrega |

É uma ordem de prioridades, não garantia de duração. Auditoria deve nascer junto das mutações, e deploy deve ser validado no início; não deixá-los para integrar apenas no último dia. Reservar um lote de teste curto para validar fechamento e outro mais longo para avaliação pública.

## 17. Definition of Done

- [ ] Código no GitHub público, sem segredos; histórico e documentação coerentes com o que foi implementado.
- [ ] `docker compose up --build` sobe aplicação/banco, aplica migrations e permite executar o seed documentado.
- [ ] URL pública estável durante avaliação; HTTPS confiável e WSS funcionando.
- [ ] Cadastro público de licitantes e contas provisionadas com login normal funcionam; permissões garantidas pelo backend.
- [ ] Leiloeiro busca objeto real, publica lote e vê resultados/total efetivamente recebido.
- [ ] Vitrine distingue estados e omite cancelados; sala funciona sem refresh.
- [ ] Interface em inglês, sem atalhos/labels demo; USD fixo, sem seletor ou badge de moeda no cabeçalho; valores `en-US` e comprovantes identificando a unidade financeira.
- [ ] Light padrão e Dark opcional funcionam nos mesmos componentes, com preferência persistida, foco/contraste acessíveis e sem páginas duplicadas ou código morto de tema/moeda.
- [ ] Carteira e reservas permanecem corretas entre usuários/lotes e sob concorrência; as fixtures reconciliam créditos iniciais, liquidação, reservas e receita do vendedor.
- [ ] Todos os fluxos de UI da seção 4.3 preservam lote, papel e estado financeiro; mobile mantém dados essenciais, imagens proporcionais e auditoria nos documentos.
- [ ] Anti-sniping aplica a fórmula escolhida e backend recusa lances vencidos.
- [ ] Cancelamento com lances exige motivo, libera só a reserva ativa do lote e mantém evidência pública.
- [ ] Fechamento transfere uma vez, credita vendedor e gera comprovante público pseudonimizado.
- [ ] Auditoria detecta alterações, inserções e remoções, incluindo último evento e exclusão total do lote, sob o modelo de ameaça definido.
- [ ] Falta de evidência produz UNVERIFIABLE e bloqueio de lances; não é apresentada como atendimento bem-sucedido da detecção em operação saudável.
- [ ] PREPARE/COMMIT/ABORT e recuperação conservadora têm testes de injeção de falhas; fluxo saudável não fica pendente.
- [ ] Met API indisponível não quebra vitrine, sala, auditoria ou comprovante existentes.
- [ ] Seed público tem um vendedor, dois clientes e lote efetivamente ao vivo.
- [ ] Testes críticos, lint e build passam; roteiro manual em duas sessões e em rede externa concluído.
- [ ] README informa limitações reais, operação, backup, decisões e uso/revisão de IA.
- [ ] Formulário oficial preenchido manualmente pelo candidato com links corretos.

## 18. README e submissão

README deve conter:

1. Objetivo, URLs públicas e explicação de que os créditos e os leilões de obras são simulados para o teste técnico, sem pagamentos reais; moeda única USD.
2. Pré-requisitos, variáveis, comandos de execução, migrations, seed e testes.
3. Credenciais das contas provisionadas e roteiro pelo login convencional para os dois papéis; saldos iniciais, reservas e comportamento idempotente de `seed-demo`. Não expor essas credenciais na interface.
4. Stack, instância única, rotas e organização do código.
5. Regras financeiras, fórmula anti-sniping e cancelamento com motivo.
6. Técnica de auditoria, canonicalização, separação de permissões, modelo de ameaça e roteiro seguro de adulteração em ambiente de teste.
7. Protocolo de confirmação e comportamento diante de crash/diário indisponível, incluindo limitação de recuperação automática e procedimento administrativo.
8. Dependência DNS/HTTPS, manutenção do servidor, backup/restauração e como garantir um lote de avaliação ao vivo por `seed-demo --ensure-live`, sem reset destrutivo, reabertura ou créditos automáticos.
9. Funcionalidades incompletas ou comportamentos inesperados, caso existam, sem classificá-los como implementados.
10. Onde IA foi usada e quais decisões, código e testes foram revisados/ajustados pelo candidato.



Informar nome/e-mail, GitHub público, repositórios adicionais se houver, URL pública obrigatória e relato de uso de IA. Enviar somente GitHub ou responder e-mail não substitui o formulário. Esta especificação não autoriza envio automático do formulário nem representa implantação já realizada.

## 19. Referências


- Met Museum Collection API, busca paginada v1.1 e detalhes v1: https://metmuseum.github.io/ — consultada em 26/10/2026.

- Caddy Automatic HTTPS: https://caddyserver.com/docs/automatic-https
- PostgreSQL, concorrência e isolamento: https://www.postgresql.org/docs/16/transaction-iso.html
- Python, flush/fsync e operações de filesystem: https://docs.python.org/3/library/os.html#os.fsync

As regras específicas de confirmação do diário são um desenho do Hammerz, não uma garantia oferecida pelas bibliotecas citadas. A implementação deve demonstrar as garantias pelos testes desta especificação.
