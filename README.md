cat > README.md <<'EOF'
# Coletor de Resumos — SBC OpenLib

Ferramenta Python para coleta automatizada de metadados
bibliográficos da busca integrada da SBC OpenLib (SOL).

## Funcionalidades

- Percorre páginas de resultados da busca.
- Coleta títulos, autores, datas, DOI e publicações.
- Extrai resumos e palavras-chave disponíveis.
- Registra URLs dos artigos e PDFs.
- Gera arquivos CSV e JSON para documentação.

## Instalação

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

## Utilização

python3 sol_exportar_busca_com_resumos.py \
  --url 'URL_COMPLETA_DA_BUSCA' \
  --esperados 48 \
  --saida resultados.csv

## Observações

Ferramenta experimental de apoio à pesquisa acadêmica.

A quantidade de registros e a qualidade dos metadados
devem ser verificadas após cada coleta.

A coleta de referências não representa triagem científica.
