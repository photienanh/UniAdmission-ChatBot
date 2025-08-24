app/
├─ backend/
│  ├─ app_.py
│  ├─ main.py
│  ├─ out/
│  ├─ instance/
│  ├─ llm/
│  │  ├─ __init__.py
│  │  ├─ gemini.py
│  │  ├─ kaggle.py
│  │  ├─ manager.py
│  │  ├─ schema.py
│  │  ├─ utils.py
│  │  └─ web_search.py
│  ├─ route/
│  │  ├─ auth.py
│  │  ├─ chat.py
│  │  ├─ kaggle.py
│  │  ├─ script.py
│  │  ├─ static.py
│  │  ├─ template.py
│  │  ├─ utils.py
│  │  └─ __init__.py
│  └─ schema/
│     ├─ auth.py
│     ├─ chat.py
│     └─ __init__.py
├─ config/
│  ├─ const.py
│  ├─ database.py
│  ├─ kaggle.py
│  ├─ llm.py
│  ├─ server.py
│  ├─ utils.py
│  └─ __init__.py
├─ core/
│  ├─ __init__.py
│  ├─ types/
│  │  ├─ kaggle.py
│  │  ├─ model.py
│  │  ├─ rag.py
│  │  ├─ role.py
│  │  └─ __init__.py
│  └─ utils/
└─ frontend/
  ├─ static/
  │  ├─ delete_account.css
  │  ├─ delete_account.js
  │  ├─ favicon.svg
  │  ├─ index.js
  │  ├─ login.css
  │  ├─ login.js
  │  ├─ register.css
  │  ├─ register.js
  │  ├─ stream.js
  │  └─ style.css
  └─ templates/
    ├─ delete_account.html
    ├─ index.html
    ├─ login.html
    └─ register.html

kaggle/
├─ server/
│  ├─ __init__.py
│  ├─ router.py
│  ├─ schema.py
│  └─ server.py
├─ vllm_worker/
│  ├─ __init__.py
│  ├─ engine_wrapper.py
│  ├─ server.py
│  ├─ server_setup.py
│  ├─ vllm_config.py
│  ├─ vllm_controller.py
│  ├─ vllm_engine.py
│  └─ vllm_runner.py
├─ vllm_kaggle_v2.ipynb
└─ web_search/
  ├─ component/
  ├─ engines/
  ├─ extract_info.ipynb
  ├─ info.csv
  ├─ info.pkl
  ├─ netloc.py
  ├─ pipeline.py
  ├─ schema.py
  ├─ search_query.py
  ├─ web_search.py
  └─ __init__.py
