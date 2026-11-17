# Dados versionados do backend

## municipios_coordenadas_ibge.csv

Latitude e longitude de cada municipio brasileiro, por codigo IBGE (7 digitos). Usado pelo comando
`popular_coordenadas_municipios` (FER-66), que preenche `core_municipio.latitude/longitude` para a tela
Mapa do Brasil.

- **Origem:** recorte das colunas `codigo_ibge`, `latitude` e `longitude` de `csv/municipios.csv` do
  repositorio https://github.com/kelvins/municipios-brasileiros, commit `975a51d6f2e7a9ee22a734a42ebd624263812f0c` (5.571 linhas).
- **Licenca:** MIT, Copyright (c) 2016 Kelvin S. do Prado. O texto inteiro, que a MIT pede que acompanhe as
  copias, esta em `LICENSE-municipios-brasileiros.txt` (original: https://github.com/kelvins/municipios-brasileiros/blob/975a51d6f2e7a9ee22a734a42ebd624263812f0c/LICENSE
- **Atualizar:** baixar o `csv/municipios.csv` de um commit fixo, recortar as tres colunas, ordenar por codigo
  e rodar o comando em ensaio (sem `--apply`), que valida o arquivo inteiro antes de gravar.
