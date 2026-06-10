# Web Search Agent

## Muc tieu

Them kha nang web search cho cac cau hoi kho, mo ho, hoac can thong tin cap nhat ma khong lam cham toan bo pipeline. Mac dinh web search tat, nen luong hien tai khong phat sinh network call.


## Cac buoc da setup

1. Tao branch rieng:

```text
feature/web_search
```

2. Cai dependency trong env `atlas_agent`:

```bash
conda run -n atlas_agent pip install langchain==0.2.0 langgraph==0.0.60
```

3. Tao router tai `agents/search_router.py` de danh dau cau can search. Router hien dua vao:

- answer la `N/A`
- cau hoi co keyword mang tinh cap nhat nhu `hiện nay`, `mới nhất`, `CEO`, `giá`, `phiên bản`

4. Tao web search adapter tai `agents/web_search.py` gom:

- `DisabledWebSearch`: mac dinh, khong goi network
- `DuckDuckGoHtmlSearch`: provider search that qua DuckDuckGo Lite HTML
- `HttpJsonWebSearch`: adapter cho search service noi bo neu sau nay co endpoint rieng
- LangChain tool `web_search` de LangGraph goi search qua interface thong nhat

5. Tao LangGraph tai `agents/web_search_graph.py` voi flow:

```text
route -> search -> finalize
```

6. Noi vao `main.py` theo cach han che phinh file:

- `main.py` van xu ly batch, retry, ghi CSV
- graph/search/router nam trong cac module rieng
- `main.py` chi goi `predict_with_search_details()` khi router bao can search

7. Them audit output `output/pred_audit.csv` de kiem tra cau nao can search va cau nao da search that.

8. Them cau hinh Docker Compose:

```text
WEB_SEARCH_ENABLED=${WEB_SEARCH_ENABLED:-false}
WEB_SEARCH_PROVIDER=${WEB_SEARCH_PROVIDER:-duckduckgo}
WEB_SEARCH_ENDPOINT=${WEB_SEARCH_ENDPOINT:-}
```

## Vi sao dung DuckDuckGo

DuckDuckGo duoc chon lam provider mac dinh cho prototype vi:

1. Khong can API key, phu hop de test nhanh trong hackathon/dev local.
2. Khong can them dependency Python ngoai; code dung `urllib` co san.
3. DuckDuckGo Lite HTML tuong doi de parse thanh cac snippet ngan cho LLM.
4. Van giu duoc kha nang thay provider sau nay bang `WEB_SEARCH_ENDPOINT` neu can dich vu on dinh hon.

Diem yeu cua DuckDuckGo HTML la khong dam bao on dinh nhu API chinh thuc. Neu len production nen doi sang search service co API ro rang nhu Tavily, SerpAPI, Brave Search API, hoac endpoint noi bo.

## Kien truc

Tinh nang duoc tach khoi `main.py` de tranh file qua dai:

- `agents/search_router.py`: quyet dinh cau nao can search.
- `agents/web_search.py`: adapter web search va LangChain tool.
- `agents/web_search_graph.py`: LangGraph flow `route -> search -> finalize`.
- `main.py`: chi goi graph khi router danh dau cau can search, sau batch/retry local.

## Luong xu ly

```text
batch answer
  -> cau hop le: giu dap an
  -> cau N/A/sai format: retry 1 lan bang prompt ep CSV
  -> router danh dau cau can search neu N/A hoac co dau hieu can thong tin cap nhat
  -> cau can search duoc dua qua LangGraph web_search
  -> neu search co context: goi model lai voi context web
  -> neu search tat/khong co context: giu N/A
```

## Khi nao can search

Router hien search khi:

- dap an hien tai la `N/A`
- cau hoi co dau hieu can thong tin cap nhat: `hiện nay`, `mới nhất`, `hôm nay`, `CEO`, `giá`, `phiên bản`, ...

## Cau hinh

Mac dinh:

```text
WEB_SEARCH_ENABLED=false
```

Neu muon bat search truc tiep bang DuckDuckGo HTML:

```text
WEB_SEARCH_ENABLED=true
WEB_SEARCH_PROVIDER=duckduckgo
```

Neu muon dung HTTP endpoint noi bo thay DuckDuckGo:

```text
WEB_SEARCH_ENABLED=true
WEB_SEARCH_ENDPOINT=http://your-search-service/search
```

Response JSON nen co mot trong cac field:

```json
{"context": "..."}
```

hoac:

```json
{"text": "..."}
```

hoac:

```json
{"snippet": "..."}
```

## Ly do dung LangChain va LangGraph

- LangChain: boc search adapter thanh `web_search` tool.
- LangGraph: tach flow route/search/finalize thanh graph ro rang, de sau nay them node confidence, cache, hoac provider search that ma khong lam phinh `main.py`.

## Audit output

`output/pred_audit.csv` co them cot:

```text
qid,answer,confidence,needs_search,search_used
```

- `needs_search=true`: router danh dau cau nay nen search.
- `search_used=true`: web search da lay duoc context va model da duoc goi lai voi context do.

## Tac dong toc do

Khi `WEB_SEARCH_ENABLED=false`, toc do gan nhu khong doi vi search adapter tra context rong.

Khi bat search, chi cac cau can search moi phat sinh network call. Neu bat search cho moi cau thi thoi gian se tang manh.
