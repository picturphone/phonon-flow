# PhononFlow

**让 AI 帮你跑通 VASP 声子计算。**

把 PhononFlow 交给你的 AI 助手（Claude / ChatGPT / 其他），它就能替你完成从配置到运行的全部流程——而你不需要懂任何技术。

---

## 给谁用的？

你如果符合下面任意一条，PhononFlow 就是为你准备的：

- 你**不会写代码**，但会用 AI 聊天
- 你**不懂 Linux 命令**，不知道 `ssh`、`scp`、`grep` 是什么
- 你**没用过 SLURM**，不知道 `sbatch` 和 `sacct` 怎么用
- 你**没碰过 VASP**，不知道怎么准备输入文件
- 你**不想学这些**，你只想算出声子谱

你不是一个人。你有一个 AI 助手——而 PhononFlow 就是让你和 AI 助手协作的工具。

---

## 能干什么？

PhononFlow 是一个 **AI 能看懂并操作的声子计算模板**。

你只需要告诉 AI 助手：
- "我要算什么材料"（提供结构文件）
- "我的集群 IP 和用户名是什么"

AI 助手就会：
1. 读取 PhononFlow 的全部代码
2. 询问你需要的配置信息
3. 帮你生成 SSH 密钥并上传到集群
4. 修改 YAML 配置文件
5. 替你提交 VASP 声子计算任务
6. 等计算完成后，自动跑 Phonopy 后处理，给你声子谱图

**你全程只需要复制粘贴和跟 AI 聊天。**

---

## 价值在哪里？

**价值一：你不需要学任何技术**

VASP 声子计算本来需要你学会：Linux 基础命令、SSH 远程连接、SLURM 作业调度、VASP 输入文件格式、Phonopy 后处理……学完这些至少几周。有了 PhononFlow，AI 替你干了所有技术活。

**价值二：每次计算省 80%~90% 的 Token**

如果你之前让 AI 帮你写 HPC 操作代码，每次都要生成几百行 `ssh`、`scp`、`sbatch` 脚本。PhononFlow 把流程固化成模板，AI 下次只需要改几个参数，不用重新写全部代码。

**价值三：你不是一个人在战斗**

你不会技术，但你有一个 AI 助手。PhononFlow 就是你们两个之间的"共同语言"——一个结构化的、AI 可操作的 HPC 流程说明书。

---

## 怎么开始？

**第一步：** 把这个仓库的链接发给你的 AI 助手。

**第二步：** 告诉 AI 助手：

> "我想用 PhononFlow 算一个材料的声子谱。这是我的结构文件：[附上文件]。我的集群 IP 是 xxx，用户名是 xxx。帮我配置并运行。"

**第三步：** 按照 AI 助手的提示，复制粘贴它给你的命令。

**然后等结果就行了。**

---

## 技术细节（给 AI 看的）

PhononFlow 是一个 Python 库 + CLI 工具，通过 SSH 远程连接 SLURM 集群，自动化执行完整的 DFT 声子计算流水线：`relax → displace → forces → bands → Raman`。配置通过 YAML 文件驱动，采用"验证优先"策略——先提交 1 个测试任务验证配置，再批量提交所有位移结构，避免算了几十个小时才发现参数错了。

### 安装

**外部工具（单独安装）：**

| 工具 | 用途 | 安装方式 |
|------|------|---------|
| [VASP](https://www.vasp.at/) | DFT 计算（HPC 集群上） | 授权软件——在集群上安装 |
| [phonopy](https://phonopy.github.io/phonopy/) | 后处理（本地） | `conda install -c conda-forge phonopy` |

**Python 依赖（自动安装）：** Python ≥ 3.10, `paramiko`, `pyyaml`, `click`, `rich`

```bash
pip install phonon-flow
```

### 命令行

```bash
# 初始化
phonon-flow init Si -e Si --crystal cubic --space-group 227

# 验证连接
phonon-flow check -c si_phonon.yaml

# 分步运行（因为 VASP 计算耗时间）
phonon-flow run -c config.yaml -s relax        # 先弛豫
phonon-flow run -c config.yaml -s displace -s forces  # 再算力常数
phonon-flow run -c config.yaml -s bands -s raman -s plot  # 最后分析

# 队列管理
phonon-flow queue -c config.yaml        # 查看作业
phonon-flow queue -c config.yaml --kill # 取消全部
```

### Python API

```python
from phonon_flow import PhononConfig, PhononWorkflow

config = PhononConfig.from_yaml("config.yaml")
wf = PhononWorkflow(config)

# 分步执行
wf.run_relax()       # 弛豫
wf.run_displace()    # 生成超胞位移
wf.run_forces()      # 力常数计算
wf.run_bands()       # 声子色散
wf.run_raman()       # Raman 活性分析
wf.render_report()   # 生成报告
```

### 配置示例

```yaml
material:
  name: Si
  potcar_elements: [Si]
  crystal_system: cubic
  space_group: 227

backend:
  type: hpc_slurm
  hpc_slurm:
    host: login.hpc.example.com
    username: YOUR_USERNAME
    keyfile: ~/.ssh/id_rsa
    partition: YOUR_PARTITION
    ntasks_per_node: 32
    vasp_bin: ~/path/to/vasp_std
    env_setup:
      - "module purge"
      - "source ~/path/to/vasp/env.sh"

phonopy:
  supercell_dim: [2, 2, 2]
  band_points: 101
```

### 架构

```
CLI (click)
  └── PhononWorkflow
        ├── relax     → HPC SLURM (SSH)
        ├── displace  → 本地 phonopy
        ├── forces    → HPC SLURM (SSH)
        ├── bands     → 本地 phonopy
        ├── raman     → 本地 phonopy
        ├── plot      → 本地 matplotlib
        └── report    → Markdown 汇总
```

### 验证

在标准 VASP/Phonopy 教程材料 **Si（金刚石, Fd-3m, #227）** 上验证通过：

| 指标 | 值 |
|------|-----|
| 超胞 | 2×2×2 = 16 原子 |
| 声子模式 | 6（3 声学 + 3 光学） |
| 稳定性 | 无虚频 |
| Raman 活性 | 1 模式（T₂g, ~520 cm⁻¹） |

## 引用

```bibtex
@software{phononflow2026,
  title = {PhononFlow: AI-Operated Phonon Calculation Workflow},
  author = {PhononFlow Contributors},
  year = {2026},
  url = {https://github.com/picturphone/phonon-flow},
}
```

本项目基于 [VASP](https://www.vasp.at/)、[phonopy](https://phonopy.github.io/phonopy/) 和 [paramiko](https://www.paramiko.org/)。

## License

MIT License.
