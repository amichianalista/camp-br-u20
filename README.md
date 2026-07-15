# Brasileiro Sub-20 2026 - Visualizacao

Aplicacao Streamlit para consultar perfis de jogadores do Campeonato Brasileiro Sub-20 2026. A tela combina dados biograficos, imagens do Supabase Storage, cluster do jogador e cards de performance por categoria.

## Visao geral

- Framework principal: Streamlit.
- Fonte de dados: Supabase.
- Tabela base padrao: `camp-br-u20.bio_jogadores`.
- Imagens: bucket `camp-br-u20-player-images`, com pastas `teams` e `players`.
- Arquivo principal: `app.py`.
- Asset local: `assets/background.png`, usado como plano de fundo.

## Fluxo da visualizacao

1. O app carrega as credenciais e configuracoes do `.env`.
2. Busca a tabela principal de jogadores no Supabase.
3. Identifica as colunas de time e jogador automaticamente, ou usa `SUPABASE_TEAM_COLUMN` e `SUPABASE_PLAYER_COLUMN`.
4. Exibe filtros na sidebar para selecionar time e jogador.
5. Renderiza:
   - hero do time com escudo;
   - nome e posicao do jogador;
   - foto do jogador;
   - cards de bio, como altura, idade, pe preferido, pais, contrato e nascimento;
   - cluster vindo de `bio_jogadores`;
   - cards de performance agrupados por categoria, com percentis e metricas brutas.

## Variaveis de ambiente

Crie um `.env` com base em `.env.example`.

```env
SUPABASE_URL=
SUPABASE_ANON_KEY=

SUPABASE_SCHEMA=camp-br-u20
SUPABASE_TABLE=bio_jogadores
SUPABASE_TEAM_COLUMN=
SUPABASE_PLAYER_COLUMN=
SUPABASE_TEAM_LOGO_BUCKET=camp-br-u20-player-images
SUPABASE_TEAM_LOGO_FOLDER=teams
SUPABASE_PLAYER_IMAGE_BUCKET=camp-br-u20-player-images
SUPABASE_PLAYER_IMAGE_FOLDER=players
```

Observacao: o `.env` real pode conter credenciais e nao deve ser versionado.

## Tabelas usadas

A base biografica vem da tabela configurada em `SUPABASE_TABLE`. Se ela nao estiver definida, o app tenta nomes candidatos como `bio_jogadores`, `jogadores_visualizacao`, `base_visualizacao`, `players`, entre outros.

O cluster do jogador fica em `bio_jogadores.cluster`.

A performance vem das tabelas de metricas por posicao:

- `fact.metrics_players.atacantes`
- `fact.metrics_players.defensores`
- `fact.metrics_players.goleiros`
- `fact.metrics_players.laterais`
- `fact.metrics_players.meias`

Cada linha de metrica ja deve trazer `categoria`, `categoria_id`, `percentil`, `metrica_id`, `valor`, `player_id` e `posicao`. O app encontra a tabela que contem o `player_id`, agrupa as linhas por `categoria` e calcula o percentil exibido no card pela media dos percentis das metricas daquela categoria. A dimensao `dim.metrics` e usada para nomes, ordem e formatacao percentual.

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
- `python-dotenv`
- `pandas`
- `numpy`
- `plotly`
- `pillow`
- `pyarrow`
- `watchdog`

## Pontos de atencao

- O app depende de `jogador_id` para foto e performance.
- O escudo do time usa `time_id`.
- As imagens sao buscadas no Supabase Storage por padrao como `teams/{time_id}.png` e `players/{jogador_id}.{jpg,jpeg,png,webp}`.
- O cluster deve estar na coluna `cluster` da tabela `bio_jogadores`.
- Alguns textos no codigo podem aparecer com acentos quebrados por encoding antigo; isso nao impede a execucao, mas vale corrigir em uma limpeza futura.
