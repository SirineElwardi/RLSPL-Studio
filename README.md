# RLSPL Studio

**RLSPL Studio** is a standalone software platform for configuring, generating, and experimentally studying **Reinforcement Learning (RL) products through Software Product Line (SPL) principles**.

The platform makes RL variability explicit. Instead of treating an RL experiment as a collection of loosely connected scripts and parameters, RLSPL represents major design choices—such as the environment, learning algorithm, optimizer, action-selection strategy, hyperparameters, and execution settings—as configurable features subject to compatibility constraints.

---

## Overview

Reinforcement Learning experiments are affected by several forms of variability:

* the selected environment;
* the learning algorithm;
* optimization choices;
* exploration and action-selection mechanisms;
* numerical hyperparameters;
* random seeds and execution conditions.

RLSPL Studio provides a structured way to manage these choices and investigate how they affect the behavior of an RL system.

The tool is designed for both:

* **beginners**, who need guidance when constructing valid RL configurations;
* **researchers**, who need controlled and reproducible variability studies.

---

## Main Features

### Configure RL Products

Build an RL configuration by selecting its main structural and numerical components.

A product can include:

* **Environment**
* **Agent / RL algorithm**
* **Optimizer**
* **Action-selection behavior**
* **Network architecture**
* **Training hyperparameters**
* **Execution parameters**

RLSPL validates compatibility between selected features before the product is executed.

---

### Constraint-Aware Configuration

Not every combination of RL components is meaningful.

RLSPL uses capability and dependency constraints to prevent or identify incompatible configurations.

Examples include:

* continuous-control algorithms require continuous action spaces;
* DQN requires a discrete action space;
* Ornstein–Uhlenbeck noise requires compatible continuous-control capabilities;
* entropy-based action sampling requires an appropriate stochastic policy;
* algorithm-specific hyperparameters are activated only when the corresponding capability is selected.

This separates **valid RL products** from arbitrary combinations of implementation options.

---

### Explore the Configuration Space

The **Explore** interface allows users to investigate valid combinations of RL features and understand the effect of changing individual configuration decisions.

RLSPL distinguishes between:

* **structural variability** — changing components such as the algorithm, optimizer, or action-selection mechanism;
* **numerical variability** — changing hyperparameters;
* **execution variability** — repeating an otherwise identical configuration under different random seeds.

---

### Variability Studies

The **Studies** interface supports controlled experiments over selected variability dimensions.

For example, a study can keep the environment and algorithm fixed while varying the action-selection strategy:

```text
Action Selection
├── Greedy
├── Random Mixture
├── Boltzmann
└── Parameter Noise
```

or the optimizer:

```text
Optimizer
├── Adam
└── RMSprop
```

or a numerical parameter:

```text
Learning Rate
├── 1e-4
├── 5e-4
└── 1e-3
```

Multiple training seeds can then be associated with each valid configuration.

The resulting experiment is generated from an explicit variability definition rather than from independently assembled scripts.

---

### Experiment Monitoring

The **Monitor** interface provides access to training and evaluation information for individual configurations and study executions.

Depending on the experiment, RLSPL records information such as:

* episode return;
* training reward curves;
* evaluation return;
* environment steps;
* success rate when defined by the environment;
* execution seed;
* configuration metadata.

Completed configurations and studies can also be revisited from the interface.

---

### Hyperparameter Optimization

RLSPL includes optional support for **Hyperparameter Optimization (HPO)**.

Users can define an active numerical search space over selected hyperparameters while preserving the surrounding RL product configuration.

Supported search strategies include:

* Random Search
* Bayesian Optimization

This allows HPO experiments to remain connected to the same explicit configuration and evaluation workflow used throughout RLSPL.

---

## Supported RL Components

### Environments

RLSPL currently includes Gymnasium environments covering discrete and continuous control.

| Environment   | Action Space | Task               |
| ------------- | ------------ | ------------------ |
| `CartPole`    | Discrete     | Balancing          |
| `Acrobot`     | Discrete     | Swing-up control   |
| `MountainCar` | Discrete     | Goal-reaching      |
| `LunarLander` | Discrete     | Landing control    |
| `Pendulum`    | Continuous   | Continuous control |

---

### Algorithms

| Algorithm  | Family                       |
| ---------- | ---------------------------- |
| Q-Learning | Value-based                  |
| DQN        | Deep value-based             |
| DDPG       | Actor-Critic / deterministic |
| SAC        | Actor-Critic / stochastic    |

Available algorithms depend on the capabilities of the selected environment.

---

### Optimizers

Currently supported:

* Adam
* RMSprop

---

### Action-Selection Behaviors

Depending on algorithm capabilities and action-space type, RLSPL supports behaviors including:

**Discrete / value-based**

* Greedy
* Random Mixture
* Boltzmann
* Parameter Noise

**Continuous / actor-based**

* Deterministic
* Gaussian Noise
* Ornstein–Uhlenbeck Noise
* Entropy Sampling

Compatibility is checked before execution.


---

## Installation

### Requirements

Recommended:

```text
Python 3.10+
pip
venv or virtualenv
Git
```

Clone the repository:

```bash
git clone <YOUR-GITHUB-REPOSITORY>
cd <YOUR-REPOSITORY>
```

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

Upgrade the packaging tools:

```bash
python -m pip install --upgrade pip setuptools wheel
```

Install RLSPL Studio:

```bash
pip install -e .
```

---

## Reproducibility and Traceability

RLSPL was developed with reproducible RL experimentation as a central objective.

For meaningful comparisons, an RL experiment should preserve information such as:

* complete product configuration;
* training seed;
* evaluation seed;
* training budget;
* software dependencies;
* environment version;
* evaluation protocol;
* checkpoint-selection policy.

RLSPL makes these decisions explicit and connects experimental outputs to the configuration from which they were produced.

A fixed configuration should **not** be interpreted as guaranteeing a fixed empirical result. RL training remains stochastic, and repeated executions of the same numerical and structural configuration may produce different learning trajectories and evaluation results.

---

## Research

RLSPL originated as a research project investigating how **Software Product Line Engineering (SPLE)** can support the systematic development and experimentation of Reinforcement Learning systems.

The research behind RLSPL currently addresses several related objectives:

* systematic management of RL variability;
* reusable RL product construction;
* configuration validity;
* experimental traceability;
* reproducibility;
* controlled variability studies;
* sensitivity analysis;
* hyperparameter exploration;
* structured evaluation.

Two publications currently document the RLSPL approach and its experimental use.

The main RLSPL paper introduces the Software Product Line approach for structuring variability and reuse in RL development:

**S. Wardi, R. Mzid, and T. Ziadi.**
*RLSPL: A Software Product Line for Streamlining Reinforcement Learning Project Development.*
**Information and Software Technology**, Volume 190, Article 107916, 2026.
DOI: `10.1016/j.infsof.2025.107916`

A second study investigates how RLSPL can support **traceability and reproducibility in RL experimentation**:

**S. Wardi, R. Mzid, and T. Ziadi.**
*How Can the RLSPL Framework Strengthen Traceability and Reproducibility in Reinforcement Learning Projects?*
In **Proceedings of the 21st International Conference on Evaluation of Novel Approaches to Software Engineering (ENASE 2026)**, Volume 1, pp. 113–124, SCITEPRESS, 2026.
DOI: `10.5220/0014836400004015`

---

## How to Cite RLSPL

If you use **RLSPL as a Software Product Line framework for constructing and managing RL products**, please cite:

```bibtex
@article{wardi2026rlspl,
  title   = {RLSPL: A Software Product Line for Streamlining Reinforcement Learning Project Development},
  author  = {Wardi, Syrine and Mzid, Rania and Ziadi, Tewfik},
  journal = {Information and Software Technology},
  volume  = {190},
  pages   = {107916},
  year    = {2026},
  doi     = {10.1016/j.infsof.2025.107916}
}
```

If you use RLSPL for **reproducibility, traceability, configurable evaluation, or hyperparameter exploration**, please also cite the ENASE paper:

```bibtex
@inproceedings{wardi2026rlsplreproducibility,
  title     = {How Can the RLSPL Framework Strengthen Traceability and Reproducibility in Reinforcement Learning Projects?},
  author    = {Wardi, Syrine and Mzid, Rania and Ziadi, Tewfik},
  booktitle = {Proceedings of the 21st International Conference on Evaluation of Novel Approaches to Software Engineering (ENASE 2026)},
  volume    = {1},
  pages     = {113--124},
  publisher = {SCITEPRESS},
  year      = {2026},
  doi       = {10.5220/0014836400004015}
}
```

For work relying on both the **RLSPL framework** and its **experimental reproducibility capabilities**, citing both publications is recommended.

---






