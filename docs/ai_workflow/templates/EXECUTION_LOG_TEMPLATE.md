# <Task ID> — <任务名称>执行记录

- Task ID：`<Task ID>`
- Prompt：[原始指令](../prompts/<类型>/<Task ID>_<名称>.md)
- 目标与验收：<实际任务范围、通过条件>
- 当前状态：PLANNED / IN_PROGRESS / REVIEW / COMPLETED / BLOCKED
- 任务 Commit SHA：<待提交 / 完整 SHA / 无，说明原因>

## 执行轮次 1：<YYYY-MM-DD HH:MM Australia/Sydney>

- AI 工具/模型：<已知型号；未知明确写未知>
- 执行前 Git 状态：<分支、HEAD、用户已有未提交文件>
- 实际改动：<逐文件写目的和内容；未改写无>
- 命令与结果：<每条重要命令、退出状态；未运行写未运行>
- 测试与验收：<命令、通过/失败/未运行及证据；不要把历史测试当本次测试>
- 问题/风险：<实际发生；根因未确认要标注>
- 决策：[<如有>](../decisions/<Task ID>-DECISION-01.md)
- Issue：[<如有>](../issues/<Task ID>-ISSUE-01.md)
- 下一步：<下一位执行者需要做的事>

## 执行轮次 2（换工具或重试时追加）

<沿用同一 Task ID，不覆盖轮次 1；分别记录工具、修改、命令和结果。>

## 更正记录（如有）

- <日期、原记录、更正原因和新事实；不隐去原始记录>
