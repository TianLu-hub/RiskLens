# RiskLens

RiskLens 是一个股票和 ETF 组合风险分析网站。输入股票代码和配置比例，就能查看这个组合过去的风险表现。它不会替你交易，也不连接证券账户。

[在线体验](https://risklens-ai-portfolio-risk-terminal.tianlu923.chatgpt.site/) · [English](README.md)

## 能做什么

- 查看收益、波动率、Sharpe 比率、回撤、历史 VaR/CVaR、相关性，以及每个持仓贡献了多少风险。
- 测试假设性的市场、科技股、利率或单只股票冲击，查看估计损益和使用的假设。
- 用 SPY 作为大盘代理，估计组合的市场暴露。
- 比较当前权重与最小波动率、最大 Sharpe、风险平价的优化权重。
- 做滚动回测：只用过去的数据求权重，再用后面的日期检验。
- 通过“风险官”用简单语言解释已经算出的结果。

默认组合是 AAPL 20%、MSFT 20%、NVDA 15%、SPY 25%、TLT 20%。可以换成自己的持仓。权重不能为负，合计必须为 100%；目前不支持空头持仓。

## 它怎么工作

~~~text
浏览器（React / TypeScript）
        |
        v
FastAPI（Python）<--- Yahoo Finance 历史日价格
        |
        +-- 风险指标、因子回归和压力测试
        +-- 组合优化和滚动回测
        +-- 风险官解释计算结果
~~~

所有金融数值都由 Python 计算，不由语言模型编造。风险官默认使用免费的规则解释模式；可选的 LLM 只帮助理解问题，不负责计算组合指标。

默认请求约三年的历史日价格，并显示实际使用的日期和观测数量。这不是交易所实时行情。如果后端暂时无法连接，前端会显示明确标注的合成数据演示快照。

## 本地运行

需要 Python 3.12+、Node.js 22.13+ 和 pnpm。从项目根目录打开两个终端。

后端：

~~~bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --env-file .env
~~~

前端：

~~~bash
cd frontend
cp .env.example .env.development.local
pnpm install
pnpm dev
~~~

打开 http://localhost:3000。后端健康检查是 http://127.0.0.1:8000/health，接口文档是 http://127.0.0.1:8000/docs。默认模式不需要 OpenAI API Key。

也可以在项目根目录运行 docker compose up --build，同时启动前后端。

## 测试

~~~bash
cd backend
.venv/bin/pytest -q
.venv/bin/ruff check app tests

cd ../frontend
pnpm lint
pnpm build
~~~

## 目录说明

- backend/app：API、行情数据接口、风险计算、优化和风险官。
- backend/tests：使用合成价格数据的单元测试与接口测试。
- frontend/app、frontend/components、frontend/lib：页面、图表和 API 客户端。
- docs：更详细的项目说明和简历描述。

## 使用边界

压力测试是简化的假设情景，不是预测，也不能精确重现历史事件。科技股暴露和债券久期可能使用明确标注的兜底假设。回测是模拟结果，没有覆盖所有真实交易成本，也不能完全排除选股时的事后偏差。历史指标和优化权重会随数据变化。

目前前端部署在 Sites，Python 后端部署在 Railway。如果换平台，前端的 NEXT_PUBLIC_API_URL 要填写公开的 HTTPS 后端地址；后端的 CORS_ORIGINS 要填写前端来源。不要把 API 密钥放进前端。

本项目用于学习和研究，不构成个性化投资建议。
