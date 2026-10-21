# Git 与公开开发纪律

默认 main 分支，工作按真实模块逐步完成。主代理是唯一提交者，子代理只在分配范围内编辑或提供证据。

每次提交前审查 `git status --short`、变更内容、数据许可、秘密和大文件；运行相称质量命令。明确列出暂存路径，检查 `git diff --cached --check` 与暂存 diff。

提交后立刻执行 `git push -u origin HEAD`，随后执行：

```powershell
git rev-parse HEAD
git ls-remote origin "refs/heads/$(git branch --show-current)"
```

SHA 一致才能进入下一工作单元。push 失败不得继续提交或实施下一模块，先检查网络、凭据、远端更新；不用 force push 掩盖冲突。授权只走 GitHub 的安全交互，不索取 Token 明文。

已公开错误用新增修复或 `git revert` 更正，禁止回填日期、改作者或重写美化历史。阶段记录引用此前已核对的 SHA，当前记录由所在 commit 自然标识，避免为补写自身 SHA 制造循环提交。

Issues 记录数据风险、研究假设与验收；常规实施由现有用户授权覆盖，涉及研究根本方向、许可不明公开资源等重大变化再请示。
