# Scout Tecnico Base BR

Aplicacao Streamlit para scouting tecnico de jogadores de base. A visualizacao agrega historico de competicoes disputadas pelos atletas e combina dados biograficos, imagens do Supabase Storage, perfil tecnico e variaveis de jogo por funcao.

## Visao geral

- Framework principal: Streamlit.
- Pasta do projeto: `scout-tecnico-base-br`.
- Fonte de dados: Supabase.
- Tabela base padrao: `jogadores-br-sub-20.player_bio`.
- Imagens: bucket `jogadores-br-sub-20`, com pastas `teams` e `players`.
- Arquivo principal: `app.py`.
- Asset local: `assets/background.png`, usado como plano de fundo.

## Fluxo da visualizacao

1. A barra lateral pequena permite alternar entre `Perfil Individual` e `Perfil por Funcao`.
2. A pagina `Perfil Individual` carrega as credenciais e configuracoes do `.env`.
3. Busca a tabela principal de jogadores no Supabase.
4. Identifica as colunas de time e jogador automaticamente, ou usa `SUPABASE_TEAM_COLUMN` e `SUPABASE_PLAYER_COLUMN`.
5. Exibe filtros no topo da pagina para selecionar time, posicao principal e jogador. A posicao principal vem das tabelas `fact.scores_players.*`, relacionada com a bio por `jogador_id`.
6. Renderiza:
   - hero do time com escudo;
   - nome e posicao do jogador;
   - foto do jogador;
   - cards de bio, como altura, idade, pe preferido, pais, contrato e nascimento;
   - cluster/persona vindo das tabelas de scores por posicao, relacionado por `jogador_id`;
   - radar de estilo de jogo usando os percentis de score;
   - tabela lateral com ranking, score bruto e percentil por categoria.

A pagina `Perfil por Funcao` agrupa os atletas por funcao ampla e persona vinda das tabelas `fact.scores_players.*`. Ao selecionar uma persona, exibe os jogadores e seus clubes logo abaixo da funcao escolhida; ao selecionar um jogador, carrega os scores por categoria a partir das mesmas tabelas.

## Variaveis de ambiente

Crie um `.env` com base em `.env.example`.

```env
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_DATABASE_URL=

SUPABASE_SCHEMA=jogadores-br-sub-20
SUPABASE_TABLE=player_bio
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

A base biografica vem da tabela configurada em `SUPABASE_TABLE`. Se ela nao estiver definida, o app tenta nomes candidatos como `player_bio`, `bio_jogadores`, `jogadores_visualizacao`, `base_visualizacao`, `players`, entre outros.

O cluster/persona exibido na visualizacao nao vem da base biografica. Ele vem sempre da coluna `persona` das tabelas de scores por posicao, com relacionamento por `jogador_id`.

A leitura tecnica usa as tabelas de scores por posicao:

- `fact.scores_players.atacantes`
- `fact.scores_players.defensores`
- `fact.scores_players.goleiros`
- `fact.scores_players.laterais`
- `fact.scores_players.meias`

Cada linha de score deve trazer `jogador_id`, `posicao`, `minutos_jogados`, `persona`, `ranking_percentil` e pares de colunas no formato `pontuacao_*` / `percentil_*`. O app encontra a tabela que contem o `jogador_id`, transforma cada par de colunas em uma categoria e exibe score e percentil.

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

- O app usa `SUPABASE_DATABASE_URL` para consultar tabelas e scores diretamente quando o PostgREST do Supabase estiver indisponivel.
- O app depende de `jogador_id` para foto e performance.
- O escudo do time usa `time_id`.
- As imagens sao buscadas no Supabase Storage por padrao como `teams/{time_id}.png` e `players/{jogador_id}.{jpg,jpeg,png,webp}`.
- O agrupamento por cluster/persona usa a coluna `persona` das tabelas `fact.scores_players.*`, relacionada por `jogador_id`.
- Alguns textos no codigo podem aparecer com acentos quebrados por encoding antigo; isso nao impede a execucao, mas vale corrigir em uma limpeza futura.
