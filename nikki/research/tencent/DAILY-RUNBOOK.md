# 每日更新腾讯研究并发布 Pages

已授权范围：每天更新腾讯研究，发布到现有 GitHub Pages。
调度：Asia/Shanghai 每日19:10启动，使用当前 Codex 任务 heartbeat。
发布地址：https://jiuchenm.github.io/money/#/tencent 。
不进行证券交易，不新建 Skill。用户已明确要求在此GitHub Pages恢复完整研究页，
包括K线和3手持仓情景；3手按100股/手计算，成本428港币用于盈亏展示。

## 1. 确认交易日和运行状态

工作根目录：C:/Users/miaonathan/workspace/money。
Python：research-private/.venv-x64/Scripts/python.exe。
先读取 AGENTS.md、本文件及 docs-site/docs/reference/tencent-research-path-v1.md。
用 Asia/Hong_Kong 当前日期和 XHKG 日历判断。非交易日保留上次报告日期，
只在私有运行日志记录检查；不把周五行情改成周末日报。
若尚未到当天18:30，不运行收盘版。特殊临时休市须取得HKEX证据后记录例外。
行情日使用XHKG，用户动作和未来三日使用已核实港股通日历，二者不可混淆。
例如9/25港股有行情但港股通无服务；10/1—7港股通关闭。交易日历跨年必须先
更新官方来源，不把港股开市自动当作内地投资者可执行日。周末修复允许补发
最近已收盘的失败日报，保留原交易日、实际补发时间及更正说明。
检查最近发布的 report_date/prediction_id。同日已成功发布且没有关键修正时退出，
不得为更新时间而重发或改写旧预测。失败可重试一次，仍失败则保留旧产物并报告。

本地调度要求电脑开机、Codex运行、目录和GitHub登录可用；Pages阅读不需要本机在线。
不得将这套本地研究描述为GitHub云端自主执行。GitHub Actions只构建部署已提交产物。

## 2. 获取私有数据和更新研究

运行 collect.py --date YYYY-MM-DD，再运行 analyze.py --date YYYY-MM-DD。
再运行 intraday.py --date 当前研究日期 --report-date 本次交易日 --collect-only。
检查30m覆盖、午休与CAS，120m只用09:30–11:30和13:00–15:00完整周期。
为新的交易日先写 research-private/tencent-intraday-当前研究日期/three-day-plan.json，
包含 market_date、plan、levels，按当日30m/120m/日线重算触发和未来3交易日，
不能复制9月22日的449/442/430等静态价位。随后 --analyze-only生成分钟分析。
日线优先Eastmoney；失败后自动选择本次成功抓取的Tencent未复权day，
必须与Yahoo最近5日OHLC一致，保持真实交易日、收盘后抓取和日历校验。
历史成交额只复用同日同价同量的已保存记录；当日可用Tencent同日收盘quote的
真实amount字段，币种/日期/量价比均须通过校验。其他缺失成交额保持null，
禁止用close乘volume或前日数据代替；周/月有缺数则合计也标缺失。
两个独立价格源均失败、抓取尚未收盘、缺交易日或末日冲突时停止发布。
分钟第二源失败可标单源降级；不得复用同目录上次抓取文件当本次成功。
外围源失败可以降级，但在报告中标出名称、最近数据日、缺失对结论的影响。
FRED失败不能当成零利率；WebIQ历史已返回AuthInvalidApiKey，不无意义重复调用。

并行按三条研究线检索：AI模型/Agent/算力工具；腾讯/中国互联网/政策；
全球科技硬件/财报/供应链与宏观。先检查近7天，再扩展至滚动30天。
维护至少100个合格科技话题，不要求每天100条新消息。可以从最近私有研究池继承
仍在窗口内的已核验事件，保留其原始时间和来源；每天重新检索新增与纠错。
如果滚动窗口内不足100，记录缺口，不凑词、拆分同一发布或伪造热度。

每条话题保留来源URL、自写摘要、发生/发布时间、精确时间未知为null、证据等级、
与腾讯的传导、关注依据。复制的全文或长引文不得进入公共数据。
同一事件跨来源/跨组去重，保留失败、竞争与成本信息，不按利好条数投票。
收盘后新闻不能解释当天涨幅；美股输入只能用当时已结束时段。

写入 research-private/tencent-YYYY-MM-DD 下：
- news-ai-compute.json、news-tencent-china.json、news-global-macro.json
- 对应检索日志、topic-exclusions.json（无排除也写空对象）
- synthesis.json：必须含 report_date、headline、summary、confidence、news、technical、
  macro、scenarios、watch、limitations。只写已计算数字，情景给触发/失效条件。
- 可选 macro-supplement.json，只纳入有官方来源和真实数据日期的当前补充。

三柱框架服从 Tide：时间线→合力→持续条件→腾讯质量/兑现→位置与触发→复盘。
更新上次成熟预测的结果；窗口未成熟不判命中。模型没有击败基线时不晋升，
不因调度而修改模型/参数寻找好看结果。每月再单独评估模型改进。

## 3. 生成、审查和导出公开产物

先运行 assemble.py --date YYYY-MM-DD，再运行 intraday.py的 --analyze-only，
后者把分钟图、3手情景和回测附加到快照并生成v2版本；不能在其后再assemble覆盖。
审查最终信息集、数字一致性、来源日期、去重、个人信息和转载范围。
用户已要求恢复完整页面。公开图表所需OHLCV、日周月与30/120m均线、跨资产摘要、
模型检验、话题与3手操作情景。保持来源/时点/缺失/竞价口径；不发布密钥、
本机路径、原始HTTP响应、pickle特征矩阵或账号数据。行情事实与原创分析区分。
胜率定义为三日期末净财富胜过始终持300股，包含未买回、踏空和双边费用。
每边0.20%是压力假设，实际券商佣金/汇兑未知，显示小样本区间，不能报虚假高胜率。
卖1/2/3手是累计仓位管理，买回只限已卖数量，总持仓上限3手；不自动下单。

审查完成后，生成 publication-review.json：
- report_date 与本次交易日一致；mode 为 full-research-page；user_authorized_full_page为true。
- reviewed_at 使用当前真实带时区时间。
- checks 中 original_summaries、market_timing_checked、no_credentials_or_local_paths
  全部为审查后的true，不提前自动签署。
- sha256 为 site-data/latest.json、synthesis.json、三个news文件、
  topic-exclusions.json 的实际文件SHA256。输入改变后必须重新审查。

运行 publish_public.py --date YYYY-MM-DD，使用x64 Python。
公开产物只在 nikki/site/public/data/tencent/latest.json 和 archive/<prediction_id>.json。
运行标准库模式的 --verify-public、标签/数据回归测试和 npm --prefix nikki/site run build。
查看 git diff --check 和公开JSON，禁止 git add -A。

## 4. 发布并验证真正上线

数据更新仅允许提交 nikki/site/public/data/tencent/latest.json 与本次新archive。
不提交用户其他dirty修改，也不自动修改源码或顶层理论。
先 git fetch origin。若主工作区有其他dirty修改或与远端不同步，使用本次独立
git worktree（位于 research-private/publish-worktrees）从最新origin/main创建，
只复制上述两份公开文件，运行公开字段校验后提交并fast-forward push HEAD:main。
禁止force push、reset用户工作或自动解决非本任务冲突。远端前进时重新基于最新
main应用这两份产物；若已存在更新日期/同版本则不覆盖。

观察 .github/workflows/nikki-daily.yml 的当前提交部署结果，不把push成功当上线。
读取 https://jiuchenm.github.io/money/data/tencent/latest.json，确认 report_date 和
prediction_id 与本次一致，并核实 #/tencent 页面可用。部署失败只报告实际失败，
不声称新日报已上线；修复不涉及重算今天的预测。

私有运行日志保存开始/结束、输入hash、质量结果、commit、Actions URL、线上id。
成功仅简报日期、关键变化和页面链接；休市/无变化不重复打扰。失败、数据过期或
需要用户操作时说明具体原因。用户明确停止时更新该自动化状态，不删除历史。
