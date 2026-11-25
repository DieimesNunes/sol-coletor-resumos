#!/usr/bin/env python3
"""Coleta preliminar de resultados da busca integrada da SBC OpenLib com resumos.

Uso:
 python3 sol_exportar_busca_com_resumos.py --url 'URL_DA_PAGINA_DE_RESULTADOS' --esperados 48

Importante: extrai apenas HTML publico, de forma gentil (pausas entre requisições),
sem contornar bloqueios. Estrutura da SOL pode mudar. Confira os resultados.
"""
import argparse
import csv
from datetime import datetime, timezone
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("Instale as dependencias no ambiente virtual: pip install requests beautifulsoup4")

ARTIGO = re.compile(r"/article/view/(\d+)(?:/|$)", re.I)
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s<>\"']+", re.I)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PesquisaAcademica/1.0; coleta de metadados publicos)",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
}
COLUNAS = ["ID", "Titulo", "Autores", "Ano", "Data_publicacao", "Publicacao", "DOI", "URL_artigo", "Resumo", "Palavras_chave", "URL_PDF", "Status_resumo"]


def normalizar(txt):
    return re.sub(r"\s+", " ", txt or "").strip()


def metatags(soup, campo):
    items=[]
    for m in soup.find_all('meta'):
        chave = (m.get('name') or m.get('property') or '').lower()
        if chave == campo.lower():
            v=normalizar(m.get('content', ''))
            if v: items.append(v)
    return items


def primeiro_meta(soup, *campos):
    for c in campos:
        vals=metatags(soup, c)
        if vals: return vals[0]
    return ''


def texto_bloco(soup, seletores, palavras_heading=()):
    for sel in seletores:
        item=soup.select_one(sel)
        if item:
            # remove heading / label for a clean field
            clone=BeautifulSoup(str(item),'html.parser')
            for x in clone.select('h1,h2,h3,h4,.label'):
                x.decompose()
            v=normalizar(clone.get_text(' ',strip=True))
            if v: return v
    for cab in soup.find_all(['h2','h3','h4']):
        if normalizar(cab.get_text(' ',strip=True)).lower().rstrip(':') in palavras_heading:
            chunks=[]
            for sibling in cab.next_siblings:
                if getattr(sibling,'name',None) in ('h2','h3','h4','section'): break
                if hasattr(sibling,'get_text'): s=normalizar(sibling.get_text(' ',strip=True))
                else: s=normalizar(str(sibling))
                if s: chunks.append(s)
            if chunks: return normalizar(' '.join(chunks))
    return ''


def info_artigo(url, html):
    soup=BeautifulSoup(html,'html.parser')
    titulo=primeiro_meta(soup,'citation_title','DC.Title','og:title')
    if not titulo:
        node=soup.select_one('h1.page_title,h1.article_title,.page_article h1')
        titulo=normalizar(node.get_text(' ',strip=True)) if node else ''
    autores=metatags(soup,'citation_author')
    if not autores:
        autores=[normalizar(e.get_text(' ',strip=True)) for e in soup.select('.item.authors .name,.authors .author .name')]
    data=primeiro_meta(soup,'citation_date','citation_publication_date','DC.Date.issued','DC.Date')
    ano=re.search(r'(?:19|20)\d{2}',data or '')
    doi=primeiro_meta(soup,'citation_doi','DC.Identifier.DOI')
    if not doi:
        for x in soup.find_all(string=re.compile(r'^\s*DOI\s*:',re.I)):
            candidato=normalizar(x.parent.get_text(' ',strip=True)) if x.parent else str(x)
            match=DOI_RE.search(candidato)
            if match: doi=match.group(0); break
    if doi:
        doi=doi.replace('https://doi.org/','').replace('http://dx.doi.org/','').strip().rstrip('.,;')
    resumo=texto_bloco(soup, ['section.item.abstract','div.item.abstract','.obj_article_details .item.abstract','.abstract','section#articleAbstract'],('resumo','abstract'))
    if not resumo:
        resumo=primeiro_meta(soup,'citation_abstract','DC.Description','description')
    palavras=texto_bloco(soup, ['section.item.keywords','div.item.keywords','.item.keywords'],('palavras-chave','keywords','palavras chave'))
    if not palavras:
        palavras=', '.join(metatags(soup,'citation_keywords')) or primeiro_meta(soup,'DC.Subject')
    publicacao=primeiro_meta(soup,'citation_journal_title','citation_conference_title','DC.Source')
    pdf=primeiro_meta(soup,'citation_pdf_url')
    if not pdf:
        a=soup.find('a',href=re.compile(r'/article/(?:view|download)/\d+',re.I), string=re.compile(r'PDF',re.I))
        if a: pdf=urljoin(url,a.get('href',''))
    return {
        'Titulo':titulo,'Autores':'; '.join(autores),'Ano':ano.group(0) if ano else '',
        'Data_publicacao':data,'Publicacao':publicacao,'DOI':doi,'URL_artigo':url,
        'Resumo':resumo,'Palavras_chave':palavras,'URL_PDF':pdf,
        'Status_resumo':'OK' if resumo else 'AUSENTE_VERIFICAR',
    }


def links_artigos(soup,url):
    encontrados=[]
    for a in soup.find_all('a',href=True):
        href=urljoin(url,a['href'])
        p=urlparse(href)
        if p.hostname not in ('sol.sbc.org.br','www.sol.sbc.org.br'): continue
        m=ARTIGO.search(p.path)
        if not m: continue
        # Canonicaliza URL eliminando subpagina /pdf ou identificadores de arquivos
        caminho=p.path[:m.end(1)]
        u=urlunparse((p.scheme,p.netloc,caminho,'','',''))
        if u not in encontrados: encontrados.append(u)
    return encontrados


def preservar_busca(link, original):
    """Mantem a query original quando a paginacao traz somente ?page=2."""
    novo=urlparse(link); antigo=urlparse(original)
    novos=dict(parse_qsl(novo.query,keep_blank_values=True))
    antigos=list(parse_qsl(antigo.query,keep_blank_values=True))
    if novo.path==antigo.path and set(novos).issubset({'page','p'}):
        resto=[(k,v) for k,v in antigos if k not in novos]
        return urlunparse((novo.scheme,novo.netloc,novo.path,'',urlencode(resto+list(novos.items())),''))
    return link


def url_proxima(soup,url,pagina_atual):
    # Primeiro tenta as estruturas de paginação, sem confundir com links de artigos.
    seletores=['.pagination a','.pages a','nav.pagination a','a[rel="next"]','a.next']
    for sel in seletores:
        for a in soup.select(sel):
            rotulo=normalizar(a.get_text(' ',strip=True))
            if rotulo == str(pagina_atual+1) or rotulo.lower() in ('>', '›', 'próximo', 'próxima', 'next', '»') or a.get('rel') == ['next']:
                href=urljoin(url,a.get('href',''))
                if '/integrada/results' in urlparse(href).path: return preservar_busca(href,url)
    # Uma segunda chance com as âncoras sem classe CSS, por ex. páginas 1,2,>,>>.
    for a in soup.find_all('a',href=True):
        if normalizar(a.get_text(' ',strip=True)) == str(pagina_atual+1):
            href=urljoin(url,a['href'])
            if '/integrada/results' in urlparse(href).path: return preservar_busca(href,url)
    return None


def buscar(session,url,pausa):
    r=session.get(url,headers=HEADERS,timeout=30)
    r.raise_for_status()
    if 'text/html' not in r.headers.get('Content-Type','text/html').lower():
        raise RuntimeError(f'O endereco nao retornou HTML: {url}')
    time.sleep(pausa)
    return r.text


def main():
    p=argparse.ArgumentParser(description='Exporta resultados da busca integrada da SOL com resumos.')
    p.add_argument('--url',required=True,help='URL completa da pagina de resultados (copiar da barra do navegador)')
    p.add_argument('--saida',default='SOL_Busca_48_com_resumos.csv')
    p.add_argument('--esperados',type=int,default=48)
    p.add_argument('--max-paginas',type=int,default=5)
    p.add_argument('--pausa',type=float,default=1.5)
    args=p.parse_args()
    if not urlparse(args.url).hostname in ('sol.sbc.org.br','www.sol.sbc.org.br'):
        p.error('A URL deve ser do dominio sol.sbc.org.br.')
    if '/integrada/results' not in urlparse(args.url).path:
        p.error('Copie a URL da pagina RESULTADO DA BUSCA, nao de um artigo.')
    s=requests.Session()
    links=[]; paginacoes=[]; visitadas=set(); atual=args.url
    for pagina in range(1,args.max_paginas+1):
        if not atual or atual in visitadas: break
        visitadas.add(atual)
        print(f'Buscando pagina {pagina}: {atual[:130]}')
        html=buscar(s,atual,args.pausa)
        soup=BeautifulSoup(html,'html.parser')
        pagina_links=links_artigos(soup,atual)
        if not pagina_links:
            raise RuntimeError('Nenhum link de artigo encontrado. A SOL pode ter alterado o HTML ou bloqueado a solicitacao.')
        print('  Links nesta pagina:',len(pagina_links))
        for u in pagina_links:
            if u not in links: links.append(u)
        paginacoes.append({'pagina':pagina,'url':atual,'links_encontrados':len(pagina_links)})
        if len(links) >= args.esperados: break
        atual=url_proxima(soup,atual,pagina)
        if not atual:
            print('AVISO: nao encontrei link para pagina seguinte.')
            break
    print('Artigos unicos identificados:',len(links))
    linhas=[]
    for i,u in enumerate(links,1):
        try:
            html=buscar(s,u,args.pausa)
            info=info_artigo(u,html)
        except requests.RequestException as exc:
            print(f'AVISO {i}/{len(links)}: falha ao ler {u}: {exc}')
            info={x:'' for x in COLUNAS}
            info.update({'URL_artigo':u,'Status_resumo':'ERRO_HTTP'})
        info['ID']=f'SOL-NOVA-{i:03d}'
        linhas.append(info)
        print(f'{i:>3}/{len(links)} | resumo={"sim" if info.get("Resumo") else "nao"} | {info.get("Titulo","")[:67]}')
    dest=Path(args.saida)
    with dest.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=COLUNAS,extrasaction='ignore')
        w.writeheader(); w.writerows(linhas)
    ok=sum(bool(x.get('Resumo')) for x in linhas)
    rel={
       'data_utc':datetime.now(timezone.utc).isoformat(),
       'url_busca':args.url,'esperados':args.esperados,'paginas':paginacoes,
       'total_links_unicos':len(links),'total_csv':len(linhas),'total_com_resumo':ok,
       'total_sem_resumo':len(linhas)-ok,'arquivo_csv':str(dest),
       'aviso':'Coleta de metadados; nao representa triagem cientifica.'
    }
    logfile=dest.with_suffix('.json')
    logfile.write_text(json.dumps(rel,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'\nCSV salvo: {dest}\nRelatorio de coleta: {logfile}\nResumos: {ok}/{len(linhas)}')
    if len(linhas) != args.esperados:
        print(f'ATENCAO: esperado {args.esperados}, coletado {len(linhas)}. NAO considere a coleta completa.')
    else:
        print('Quantidade de registros confere. Verifique 3 resumos manualmente antes de usar.')

if __name__=='__main__': main()
