# Flow Web Search

Tai lieu nay mo ta flow web search khi chay `main.py` tren local.

## 1. Tong quan

Pipeline khong search web ngay tu dau. He thong luon goi model local truoc de lay dap an ban dau, sau do moi quyet dinh cau nao can web search.

Flow tong quat:

```text
read CSV
  -> chia batch
  -> predict_batch bang model local
  -> retry cac cau N/A tung cau
  -> apply_web_search cho cau can search
  -> ghi pred.csv
  -> ghi pred_audit.csv
```

Cac file chinh:

- `main.py`: dieu phoi pipeline, ghi output va audit.
- `agents/search_router.py`: quyet dinh cau nao can search.
- `agents/web_search.py`: chon search client va goi provider.
- `agents/web_search_graph.py`: LangGraph flow `route -> search -> finalize`.

## 2. Buoc doc input

`main.run()` doc file CSV tu `data/public_test.csv` theo mac dinh, normalize header BOM neu co, va bo qua row khong co `qid`.

Input row can co cac cot:

```text
qid,question,A,B,C,D
```

Sau do danh sach row duoc chia batch theo `BATCH_SIZE`, mac dinh la `20`.

## 3. Goi model local truoc

Voi moi batch, `predict_batch()` tao prompt CSV bang `rows_to_prompt()` va goi:

```python
agent(rows_to_prompt(rows))
```

Output model duoc parse boi `parse_model_answers()` de lay map:

```python
{qid: answer}
```

Dap an hop le chi gom:

```text
A, B, C, D, N/A
```

Neu model tra loi sai format, thieu qid, hoac dap an khong hop le thi cau do co the thanh `N/A`.

## 4. Retry cau N/A

Sau batch prediction, `retry_bad_rows()` chon cac row co dap an hien tai la `N/A` va goi lai model tung cau bang prompt ep format:

```text
Chi tra ve dung 2 dong CSV: header qid,answer va mot dong dap an cho qid nay.
```

Muc tieu cua buoc nay la sua loi format/output truoc khi dung web search.

## 5. Khi nao web search duoc goi

Sau retry, `apply_web_search()` xet tung row:

```python
current_answer = answers.get(qid, "N/A")
if not should_search(row, current_answer):
    continue
```

Nghia la web search chi duoc goi khi `should_search()` tra ve `True`.

`should_search()` nam trong `agents/search_router.py`. Router tra ve `True` trong 2 nhom truong hop.

### 5.1. Dap an hien tai la N/A

Neu dap an sau batch va retry van la `N/A`, router coi day la cau can them thong tin:

```python
if normalized_answer == "N/A":
    return SearchDecision(True, "answer_is_na")
```

### 5.2. Cau hoi co keyword can tra cuu

Router lower-case cau hoi va tim keyword trong `VOLATILE_KEYWORDS`.

Cac nhom keyword hien co gom:

- thoi gian/cap nhat: `hien nay`, `moi nhat`, `hom nay`, `nam nay`, `latest`, `current`, `today`
- chuc danh/nhan su: `ceo`, `chu tich`, `tong thong`
- gia/thi truong: `gia`, `co phieu`, `chung khoan`
- thong ke: `thong ke`, `dan so`, `gdp`, `dien tich`, `san luong`
- mon hoc/kien thuc can tra cuu: `toan`, `hoa hoc`, `vat ly`, `dia ly`
- phien ban: `phien ban`

File code co ca bien the co dau va khong dau cho nhieu keyword tieng Viet.

Neu match keyword, reason noi bo co dang:

```text
volatile_keyword:<keyword>
```

## 6. Search client duoc chon nhu the nao

Trong `main.run()`:

```python
search_client = search_client or default_web_search()
```

Neu test hoac code khac truyen san `search_client`, pipeline dung client do. Neu khong truyen, `default_web_search()` trong `agents/web_search.py` se chon theo environment.

### 6.1. Mac dinh local

Neu khong set env, local mac dinh dung DuckDuckGo:

```text
WEB_SEARCH_ENABLED=true
WEB_SEARCH_PROVIDER=duckduckgo
```

Tuc la `default_web_search()` tra ve `DuckDuckGoHtmlSearch()`.

### 6.2. Tat web search

Neu muon tat search:

```bash
WEB_SEARCH_ENABLED=false python main.py
```

Cac gia tri tat duoc chap nhan:

```text
0, false, no, off
```

Khi tat, client la `DisabledWebSearch`, moi lan search se tra context rong.

### 6.3. Dung HTTP endpoint rieng

Neu co `WEB_SEARCH_ENDPOINT`, code dung `HttpJsonWebSearch`:

```bash
WEB_SEARCH_ENDPOINT=http://your-search-service/search python main.py
```

Endpoint duoc goi voi query param `q` va response JSON nen co mot trong cac field:

```json
{"context": "..."}
```

hoac `text`, `snippet`.

### 6.4. DuckDuckGo HTML

Neu provider la DuckDuckGo, code goi:

```text
https://lite.duckduckgo.com/lite/?q=<question>
```

Sau do parse HTML de lay toi da 3 snippet. Neu request loi, timeout, khong co mang, hoac HTML khong match parser, context se rong.

## 7. LangGraph flow

Khi can search, `predict_with_search_details()` build graph:

```python
build_web_search_graph(search_client, answer_with_search_context)
```

Graph gom 3 node:

```text
route -> search -> finalize
```

### 7.1. route

`route_node()` goi lai router:

```python
state["needs_search"] = should_search(state["row"], state.get("answer", "N/A"))
```

Neu `needs_search=false`, graph di thang den `finalize`.

### 7.2. search

`search_node()` lay question va goi LangChain tool:

```python
question = state["row"].get("question", "")
state["search_context"] = search_tool.invoke(question)
```

Tool nay boc quanh `search_client.search(query).context`.

### 7.3. finalize

`answer_node()` co 2 nhanh:

Neu co `search_context` khac rong:

```python
state["final_answer"] = answer_with_context(state["row"], state["search_context"])
```

Luc nay model local duoc goi lai voi prompt co `Ngu canh web` va chi tra ve CSV `qid,answer`.

Neu `search_context` rong:

```python
state["final_answer"] = state.get("answer", "N/A")
```

Tuc la giu dap an cu, khong goi lai model voi web context.

## 8. Khi nao audit search_used la true

`predict_with_search_details()` tra ve:

```python
search_used = bool(result.get("search_context"))
```

Sau do `apply_web_search()` chi add qid vao `search_used_qids` khi `search_used=True`:

```python
if search_used:
    search_used_qids.add(qid)
    answers[qid] = searched_answer
```

Cuoi pipeline, `build_audit_rows()` ghi:

```python
"search_used": "true" if qid in search_used_qids else "false"
```

Vi vay `search_used=true` chi co nghia la:

1. router danh dau cau nay can search,
2. search client lay duoc context khac rong,
3. model da duoc goi lai voi context do.

## 9. Y nghia cac trang thai audit

### needs_search=false, search_used=false

Cau khong bi router danh dau can search. Pipeline giu dap an local.

### needs_search=true, search_used=false

Router muon search, nhung web context rong. Nguyen nhan thuong gap:

- `WEB_SEARCH_ENABLED=false`
- may local khong co network
- DuckDuckGo timeout/chan request
- HTML search result thay doi lam parser khong lay duoc snippet
- HTTP endpoint tra JSON khong co `context`, `text`, hoac `snippet`

Trong truong hop nay answer van la dap an cu truoc web search.

### needs_search=true, search_used=true

Web search co context va model da duoc hoi lai voi context. Answer trong `pred.csv` la answer sau buoc web search.

## 10. Vi du flow mot cau

Input:

```csv
qid,question,A,B,C,D
1,CEO hiện nay của công ty X là ai?,a,b,c,d
```

Flow:

1. `predict_batch()` goi model local, vi du tra `A`.
2. `retry_bad_rows()` khong retry vi dap an khong phai `N/A`.
3. `should_search(row, "A")` thay keyword `ceo` hoac `hien nay`, tra `True`.
4. Graph chay node `search`, goi DuckDuckGo hoac endpoint.
5. Neu context khac rong, `answer_with_search_context()` goi lai model voi context.
6. Dap an moi duoc cap nhat vao `answers`.
7. Audit ghi `needs_search=true`, `search_used=true`.

## 11. Lenh chay local

Chay mac dinh, web search bat:

```bash
python main.py
```

Tat web search:

```bash
WEB_SEARCH_ENABLED=false python main.py
```

Dung endpoint rieng:

```bash
WEB_SEARCH_ENDPOINT=http://your-search-service/search python main.py
```

Doi batch size:

```bash
BATCH_SIZE=10 python main.py
```
