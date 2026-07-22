# Scout Tecnico Base BR

Aplicacao Streamlit para scouting tecnico de jogadores de base. A visualizacao agrega historico de competicoes disputadas pelos atletas e combina dados biograficos, imagens do Supabase Storage, perfil tecnico e variaveis de jogo por funcao.

## Visao geral

- Framework principal: Streamlit.
- Pasta do projeto: `scout-tecnico-base-br`.
- Fonte de dados: Supabase.
- Tabela base padrao: `jogadores-br-sub-20.bio_jogadores`.
- Imagens: bucket `jogadores-br-sub-20`, com pastas `teams` e `players`.
- Arquivo principal: `app.py`.
- Asset local: `assets/background.png`, usado como plano de fundo.

## Fluxo da visualizacao

1. A barra lateral pequena permite alternar entre `Perfil Individual` e `Perfil por Funcao`.
2. A pagina `Perfil Individual` carrega as credenciais e configuracoes do `.env`.
3. Busca a tabela principal de jogadores no Supabase.
4. Identifica as colunas de time e jogador automaticamente, ou usa `SUPABASE_TEAM_COLUMN` e `SUPABASE_PLAYER_COLUMN`.
5. Exibe filtros no topo da pagina para selecionar time, posicao principal e jogador.
6. Renderiza:
   - hero do time com escudo;
   - nome e posicao do jogador;
   - foto do jogador;
   - cards de bio, como altura, idade, pe preferido, pais, contrato e nascimento;
   - cluster vindo de `bio_jogadores`;
   - cards de variaveis tecnicas agrupadas por tipo de acao em campo.

A pagina `Perfil por Funcao` agrupa os atletas por funcao ampla e cluster. Ao selecionar um cluster, exibe os jogadores e seus clubes; ao selecionar um jogador, carrega os scores por categoria a partir das tabelas tecnicas do Supabase.

## Variaveis de ambiente

Crie um `.env` com base em `.env.example`.

```env
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_DATABASE_URL=

SUPABASE_SCHEMA=jogadores-br-sub-20
SUPABASE_TABLE=bio_jogadores
SUPABASE_TEAM_COLUMN=
SUPABASE_PLAYER_COLUMN=
SUPABASE_POSITION_COLUMN=
SUPABASE_TEAM_LOGO_BUCKET=jogadores-br-sub-20
SUPABASE_TEAM_LOGO_FOLDER=teams
SUPABASE_PLAYER_IMAGE_BUCKET=jogadores-br-sub-20
SUPABASE_PLAYER_IMAGE_FOLDER=players
```

Observacao: o `.env` real pode conter credenciais e nao deve ser versionado.

## Tabelas usadas

A base biografica vem da tabela configurada em `SUPABASE_TABLE`. Se ela nao estiver definida, o app tenta nomes candidatos como `bio_jogadores`, `jogadores_visualizacao`, `base_visualizacao`, `players`, entre outros.

O cluster do jogador fica em `bio_jogadores.cluster`.

A leitura tecnica vem das tabelas de indicadores por posicao:

- `fact.metrics_players.atacantes`
- `fact.metrics_players.defensores`
- `fact.metrics_players.goleiros`
- `fact.metrics_players.laterais`
- `fact.metrics_players.meias`

Cada linha de indicador deve trazer `categoria`, `categoria_id`, `percentil`, `metrica_id`, `valor`, `player_id` e `posicao`. O app encontra a tabela que contem o `player_id`, agrupa as linhas por `categoria` e exibe uma leitura relativa do atleta dentro do grupo da mesma funcao. A dimensao `dim.metrics` e usada para nomes, ordem e formatacao.

## Como rodar

Instale as dependencias e execute o Streamlit:

```powershell
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\streamlit.exe run app.py
```

Se preferir usar Python diretamente:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Dependencias principais

- `streamlit`
- `supabase`
- `psycopg[binary]`
- `python-dotenv`
- `pandas`
- `numpy`
- `plotly`
- `pillow`
- `pyarrow`
- `watchdog`

## Pontos de atencao

- O app usa `SUPABASE_DATABASE_URL` para consultar tabelas e metricas diretamente quando o PostgREST do Supabase estiver indisponivel.
- O app depende de `jogador_id` para foto e performance.
- O escudo do time usa `time_id`.
- As imagens sao buscadas no Supabase Storage por padrao como `teams/{time_id}.png` e `players/{jogador_id}.{jpg,jpeg,png,webp}`.
- O cluster deve estar na coluna `cluster` da tabela `bio_jogadores`.
- Alguns textos no codigo podem aparecer com acentos quebrados por encoding antigo; isso nao impede a execucao, mas vale corrigir em uma limpeza futura.
