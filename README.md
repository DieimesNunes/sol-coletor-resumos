# Coletor de metadados e resumos — SBC OpenLib (SOL)

Script em Python para coletar, a partir de uma **busca integrada na SBC OpenLib**, os títulos, autores, datas, DOI, evento, resumos, palavras-chave e links de artigos e PDFs.

Projeto experimental de apoio a um **Mapeamento Sistemático da Literatura sobre chatbots no ensino de programação**. Não é uma ferramenta oficial da SBC, nem realiza triagem de artigos automaticamente.

## 1. O que é necessário

- Python 3 instalado (Linux Mint, Ubuntu ou outro sistema com Python).
- Internet para acessar `https://sol.sbc.org.br/`.
- Bibliotecas `requests` e `beautifulsoup4`.
- O endereço completo **da página de resultados da busca integrada**, não o endereço de um artigo isolado.

## 2. Instalar no Linux (passo a passo)

Abra o terminal e execute **um comando de cada vez**:

```bash
git clone https://github.com/DieimesNunes/sol-coletor-resumos.git
cd sol-coletor-resumos
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

O terminal deverá mostrar `(.venv)` enquanto o ambiente virtual estiver ativado.

Para trabalhar novamente em outro dia:

```bash
cd sol-coletor-resumos
source .venv/bin/activate
```

Para sair do ambiente virtual: `deactivate`.

## 3. Fazer uma busca na SOL

1. Acesse **https://sol.sbc.org.br/busca/**.
2. Selecione as fontes (por exemplo, **Anais de Eventos**).
3. Digite sua expressão, selecione os campos e execute a pesquisa.
4. Na página **Resultado da busca**, copie **todo o endereço da barra do navegador**. Ele pode ser longo; isso é normal.

**Exemplo de string exploratória utilizada em 24/11/2026:**

```text
(chatbot OR ChatGPT OR "agente conversacional") AND (programação OR programming OR algoritmos)
```

Configuração: `Anais de Eventos`, campo `Qualquer lugar`, sem filtros de data e idioma. Foram mostrados **48 registros** (25 na primeira página, 23 na segunda). Esses 48 resultados são um caso de uso, **não um limite do programa**.

## 4. Executar a coleta

Substitua `COLE_AQUI_A_URL_COMPLETA` pelo endereço completo copiado do navegador.

```bash
python3 sol_exportar_busca_com_resumos.py \
  --url 'COLE_AQUI_A_URL_COMPLETA' \
  --esperados 48 \
  --max-paginas 5 \
  --pausa 1.5 \
  --saida SOL_T1_48_com_resumos.csv
```

**Por que colocar a URL entre aspas simples?** Porque ela contém caracteres como `&`, `?`, `(` e `)`, que podem ser interpretados pelo terminal.

### Parâmetros

| Parâmetro | Significado | Obrigatório / padrão |
|---|---|---|
| `--url` | URL completa da página de resultados da **busca integrada** | **Obrigatório** |
| `--esperados` | Quantidade de registros mostrada pela busca; serve para conferir a coleta | Padrão: `48` |
| `--max-paginas` | Máximo de páginas de resultados a percorrer | Padrão: `5` |
| `--pausa` | Intervalo, em segundos, entre requisições ao site | Padrão: `1.5` |
| `--saida` | Nome do CSV gerado | Padrão: `SOL_Busca_48_com_resumos.csv` |

**Nova busca com 200 resultados?** Use outra URL, `--esperados 200`, mais páginas (por exemplo, `--max-paginas 12`) e outro nome de saída. A quantidade real pode variar; confirme a paginação no site e aumente `--max-paginas` se necessário.

## 5. Arquivos gerados

Se você escolher `--saida SOL_T1_48_com_resumos.csv`, o programa criará:

- **`SOL_T1_48_com_resumos.csv`**: tabela de metadados para Excel ou Google Planilhas.
- **`SOL_T1_48_com_resumos.json`**: relatório técnico com URL pesquisada, data UTC, páginas visitadas, links encontrados, quantidade final e contagem de resumos.

**O JSON não é um segundo conjunto de artigos.** Ele documenta a execução para permitir conferência e reprodutibilidade.

O CSV contém colunas para: ID, título, autores, ano, data de publicação, publicação, DOI, URL do artigo, resumo, palavras-chave, URL do PDF e status do resumo.

### Importação para Google Planilhas

1. Crie uma **nova aba vazia** em sua planilha de pesquisa.
2. Vá a **Arquivo → Importar → Fazer upload** e selecione o CSV.
3. Escolha **Substituir página atual**, nunca **Substituir planilha**.
4. Defina **Vírgula** como separador e conclua.
5. Confira a quantidade de linhas: **1 cabeçalho + número de registros**.

## 6. Validar o resultado (obrigatório)

1. Compare a quantidade do CSV com a quantidade exibida pela SOL.
2. Confira os campos **título, DOI, resumo e URL** em pelo menos três páginas de artigos.
3. Verifique linhas com resumo em branco ou mensagens substitutivas.
4. Preserve a string exata, o escopo, a data e o endereço da busca.

**Limitação conhecida da versão inicial:** se a página contém a frase “Este artigo não possui um resumo.”, o script pode contá-la como texto de resumo. Na primeira coleta, houve **48 linhas, mas 47 resumos efetivos e um aviso de ausência**. Portanto, **48/48 no relatório JSON não comprova 48 resumos válidos**. Essa detecção precisa ser melhorada em uma atualização do programa.

Um registro na busca **não** significa que o artigo é elegível: a triagem por critérios científicos é separada e depende de leitura humana.

## 7. Problemas frequentes

- **`python3: command not found`**: instale o Python 3 pelo gerenciador de pacotes de seu sistema.
- **`ModuleNotFoundError: requests` ou `bs4`**: ative o `.venv` e execute `python3 -m pip install -r requirements.txt`.
- **`Nenhum link de artigo encontrado`**: confira se a URL é da **página de resultados da busca integrada** e se o site não mudou sua estrutura.
- **Coletou menos registros que `--esperados`**: confira a quantidade de páginas, aumente `--max-paginas` e revise eventuais erros de rede; não declare a coleta completa.
- **Apareceram menos resumos do que artigos**: isso pode ser ausência real na página ou problema de extração; verifique manualmente.
- **Caracteres especiais / acentuação**: o CSV é escrito em UTF-8 com BOM (`utf-8-sig`) para facilitar a leitura em planilhas.

## 8. Reprodutibilidade e limitações

O programa coleta somente informações disponíveis nas páginas públicas e aplica pausas entre as requisições. A estrutura HTML, a paginação e a disponibilidade do site podem mudar; os dados precisam ser auditados após cada execução. Respeite as condições de uso da plataforma e evite volumes excessivos de requisições.

**Não se deve interpretar a coleta como triagem ou inclusão definitiva no MSL.** É necessário definir e documentar critérios de seleção, recuperar textos completos quando apropriado e verificar duplicatas.

## 9. Arquivos do repositório

- `sol_exportar_busca_com_resumos.py` — script de coleta.
- `requirements.txt` — dependências Python.
- `.gitignore` — exclui ambientes virtuais e arquivos temporários.
- `README.md` — estas instruções.

O histórico de commits documenta as alterações do projeto.
