# KCoder 2.0.29：静态核查、评分对齐与现场配置

核查日期：2026-11-18—19。只读取用户提供的安装包与本地规则文件；未执行Windows EXE、未安装Android APK、未激活账号、未发模型请求、未验证远程连接或夜间运行。原安装包保持不变。

## 1. 先纠正旧资料结论

重新读取当前本地文件 `doc/2026世界计算大会 Central Park 开源智算青年训练营 · 比赛规则 (1).pptx`（位于本资源库上级工作区）：

- **第4页明确列出“指定模型：Baize omni模型”**。本库早期资料里“规则未列为必需”的说法已过时，以本次实际回读结果替代；资料先后更新时间未独立核定。
- 第12页标题为“系统自动评分的四个维度,人工复审”，并写明“由评分系统模型同步自动评分，系统实时跑分；12:00硬截止后自动汇总成绩，现场出结果”。
- 第10页规定四件套：完整项目代码、部署或运行入口、项目说明、**演示视频**；视频在这份规则里是提交项，不只是可选备份。
- 第6—7页远程路径仍列KCoder连接器→飞书/企业微信。用户现提供官方拟下发移动APK；其是否替代/补充上述路径需按现场通知确认，文件存在不证明已获批准。
- 用户补充“选前几名做代码审计后给最终结果”。PPT只写人工复审，未给出复审人数/代码审计流程，不将用户口头信息伪装成PPT原文。

## 2. 官方四维原文与执行映射（第12页）

| 维度 | 原文说明 | 配置采取的工作法 | 复核证据 |
|---|---|---|---|
| 功能完成度 | 作品能否跑通，核心功能是否实现 | 先单局闭环，传感器与回退分别验收 | 启动、核心用例、真实设备、演示视频 |
| 代码质量 | 架构是否规范，代码是否可维护 | 输入/核心/渲染分离，小范围修改，回归测试 | 文件边界、真实命令结果、依赖锁、来源许可 |
| Agent 运行效率 | Token 消耗是否合理，任务完成率如何 | 按需上下文、定向读文件、任务止损、实测用量、减少重复派发 | 有意义任务的验收产出、平台计量口径、失败与取消记录 |
| 创新度 | 应用场景与交互方式是否有新意 | 基线→一个差异机制→最小试玩验证→演示 | 差异交互实现位置、参考、真实观察与限制 |

没有官方权重、具体Token扣分阈值、Token/完成任务公式、缓存折扣、评分器上下文或模型提示词；也没有证据表明文件写得越长、任务拆得越碎或Agent越多分数越高。配置不对评分器下指令。

## 3. 两个文件的身份

| 文件 | 字节数 | SHA-256 |
|---|---:|---|
| KCoder-Studio-Setup-2.0.29-win-x64.exe | 461830944 | `704e6a4b87be1b4b92dd81470356b99601d7e9bb52ef09526e2470b8e3531830` |
| kcoder-studio-mobile-2.0.29-android-arm64-v8a-v51.apk.1 | 72497656 | `3c502e7378adff01220f5da59d648a897cb822a158a88b35b2817819360300fe` |

Windows包是NSIS安装器，含 `resources/app.asar` 与 `resources/bin/kcoder.exe`；ASAR内 `package.json` 为 `@kcoder/studio`、版本2.0.29、入口 `desktop/main.mjs`。安卓ZIP内 `assets/app.config` 标为KCoder 2.0.29、包名 `dev.kcoder.studio`、versionCode 51、scheme `kcoder-studio`。配置中既有permissions也有blockedPermissions，**未将其当合并AndroidManifest或真实授权状态**。

## 4. 指令文件读取的静态证据

Windows包内 `resources/bin/kcoder.exe` 的可检索字符串（下列为本次提取文件的首个字节偏移）：

| 搜索文本 | 偏移 |
|---|---:|
| `AGENTS.mdKCODER.md`（相邻字符串） | 134544699 |
| `found AGENTS.md at ` | 134544718 |
| `found KCODER.md at ` | 134544851 |
| `crates/kcoder_config/src/project_instructions.rs` | 135292423 |
| `# Project Instructions` | 141568584 |

同一区域有 `project_instruction_encoding:`、`must contain UTF-8 text`、单文件及完整guide集合长度限制的错误文案。未恢复源码/常量，不推断精确限制值或读取优先级。

前端 `resources/renderer-dist/assets/i18n-1G8qPAdT.js` 有原文：

> 这份 AGENTS.md 已由原生项目指令读取，将复用原文件；不会重复注入，撤销也不会删除原文件。

> 已设为启用，之后符合范围的新会话可使用；已有会话保持原快照。

这些内容强烈支持优先用项目级 `AGENTS.md`，而非自行命名 `Agent.markdown`。但静态文案不证明自动加载、继承范围、优先级、现场后端版本和权限均已实际生效。配置包因此提供新会话加载探针与日志/上下文核查流程。

## 5. 用量/预算不是Markdown参数

`resources/renderer-dist/assets/TaskWorkspacePage-BgjtTX0C.js` 中有 `tokensUsed`、`tokenBudget`、`budgetLimited`；中文界面文案有“已记录 Token”“已记录 Token 预算”“已记录执行时间”。它们是相关Goal/任务信息可展示的线索，不证明：

- 普通参赛账号可设置任何预算；
- `tokenBudget`一定是团队总配额或按哪种输入/输出/缓存口径计算；
- 文件中的“节约Token”文字能强制限制模型上下文、关停Agent或改变计费；
- 保存在画布/任务板里的任务会自动整夜执行。

因此只提供有操作含义的节省规则，并要求现场检查实际平台设置；不生成未经验证的JSON配置键，不去调用隐藏接口，不调整系统或评分链路。

## 6. 配置包与Token策略

入口：[templates/kcoder-match/README-现场配置.md](../templates/kcoder-match/README-现场配置.md)。

- **常驻层**：[AGENTS.md](../templates/kcoder-match/AGENTS.md)，只保留稳定操作规则，避免把全套调研塞进每次请求。
- **按需层**：PROJECT（项目/创新事实）、TASKS（工单）、EVIDENCE（计量/验收/审计）。记录按里程碑更新，不逐轮写长报告。
- **任务策略**：一个可验收切片、一个默认执行Agent，真正互不冲突才加辅助；不以省Token取消测试。
- **失败策略**：相同问题不反复盲试，改用有证据的根因实验，两轮针对修复仍失败则记录阻塞并转其他就绪任务。
- **预算策略**：先读取实际额度与计量范围；团队建议将当时剩余额度30%留给集成回归，不是官方阈值，不把200万Token当已发额度。
- **创新工作**：PROJECT已整理三个此前候选的“基线/差异机制/最小实验”；均未选定、未实现、未做用户测试，避免将假设当成果。

真实目标是单位有效开销获得更多可复核成果，而非Token总数最低；没有测量就不承诺节省百分比。

## 7. 本次验证边界

已做：重读规则PPT、静态解包、包身份与SHA-256计算、指令读取字符串定位、前端文案/字段核查、模板路径和UTF-8校验、Markdown差异检查。准备目录内保留本次 `inspect_kcoder_static.py` 与 `static-evidence.json` 以便本机复核，提取的大文件不进资源库。

待现场：Windows安装/启动、AGENTS加载、上下文/计量口径、原生预算限制、移动配对/批准链路、夜间持续执行、停止条件、真实项目构建与功能测试。静态审阅不替代这些验收。

## 8. Skill格式与设置：新增静态核查

同一`resources/bin/kcoder.exe`在字节偏移`144339672`处存在内置`KCoder skill requirements:`，明确写出：

- 默认位置`.kcoder/skills/<name>/`；入口`SKILL.md`从YAML frontmatter开始，至少有`name`、`description`。
- 名称最多64字符，以小写ASCII字母或数字开头，只含小写ASCII字母、数字、`.`、`_`、`-`。
- `description`以`Use when`开头，第三人称，仅说明触发条件，不概括执行流程；正文应有触发指引、流程、陷阱和验收标准，并有不点名技能的触发测试。

这是包内置要求的静态证据，不是恢复出的完整解析器。`152045695`附近另有`SKILL.md must be UTF-8`、`SKILL.md must declare a name`、`Invalid skill frontmatter`等解析错误；未推定未知可选字段、大小上限或自动发现优先级。本包只用最小`name`和`description`，没有模型覆盖、shell注入、自动授权或其他宿主字段。

前端`resources/renderer-dist/assets/PluginManagementPage-C2oWlHNH.js`有技能页签、目录导入表单（`data-testid=kcoder-skill-import`）以及`skills/import`传`params:{path:e}`的代码，启停使用`skills/setEnabled`，收据要求`appliesToNewConversations`。只读源码，未调用这些RPC。

`resources/renderer-dist/assets/i18n-1G8qPAdT.js`有原文：

> 所选主机上的技能目录（包含 SKILL.md）

> 保存至当前目标账号，适用于该账号的所有项目。新会话使用这些设置；已载入会话的技能内容不会自动移除。停用会保留安装内容。

同包还有专家个性化“导入文件”的不同入口，文案写“支持 SKILL.md 或本页导出的 JSON，仅导入入口指令，不包含配套文件”“导入后默认停用”，启用保存后用于该专家后续轮次。它与上述主机目录导入/账号级开关不是同一作用域，不混为一个设置。

[Skill现场手册](../templates/kcoder-match/SKILLS-现场安装.md)逐一写出项目目录→实际技能列表→必要时目录导入→启用→新会话→加载证据→失败手动读取。三个技能自带项目适用边界和测试探针，但边界文字不是运行沙箱。没有把其他平台的`.claude/skills`或`.codex/skills`当KCoder配置。

## 9. 可复核的包与验证

[完整配置ZIP](../downloads/KCoder-2.0.29-agent-config.zip)含11个源文件和1份SHA-256清单；仅为本库的文本模板/脚本，不含厂商二进制或凭据。清单是完整性检查，不是数字签名。

维护者可运行`python3 tools/verify_kcoder_bundle.py --self-test`，检查文件集合、UTF-8、三个Skill的本包限制格式、名称/路径、文档链接、哈希，并进行8项拒收回归测试。该工具不是KCoder解析器，不声称证明原生运行兼容。

可选Windows安装脚本先校验所有源文件和目标冲突，再复制8个配置文件；已有不同内容要人审合并，不自动覆盖。PowerShell在本机未安装，脚本仅经静态检查，并提供不依赖脚本的手动安装。现场仍需完成原生发现/启用/加载、实际模型与计量、连接和夜间执行验收。
