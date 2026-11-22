# Monte Carlo Option Pricer (C++)

A production-style European option pricer using Monte Carlo simulation, built as a portfolio project for quantitative finance roles.

## What This Demonstrates

| C++ Concept | Where to Find It |
|---|---|
| RAII & Smart Pointers | `MonteCarloPricer.h` — `unique_ptr<Option>` ownership |
| Move Semantics | `MonteCarloPricer.cpp` — `std::move(option)` |
| Polymorphism & Virtual Functions | `Option.h` — abstract base class |
| `override` & `= delete` | `EuropeanOption.h`, `RandomNumberGenerator.h` |
| Namespaces vs Classes | `BlackScholes.h` — stateless functions in namespace |
| Const Correctness | Throughout — `const` methods, `const` references |
| STL Algorithms | `MonteCarloPricer.cpp` — `accumulate`, `transform` |
| Lambda Expressions | `MonteCarloPricer.cpp` — variance calculation |
| Modern RNG (`<random>`) | `RandomNumberGenerator.h` — Mersenne Twister |
| Member Initializer Lists | All constructors |
| CMake Build System | `CMakeLists.txt` |
| Unit Testing | `tests/test_pricer.cpp` |

## Project Structure

```
mc-pricer/
├── CMakeLists.txt
├── README.md
├── include/
│   ├── Option.h                  # Abstract base class
│   ├── EuropeanOption.h          # Concrete European option
│   ├── BlackScholes.h            # Analytical pricer (validation)
│   ├── MonteCarloPricer.h        # Monte Carlo engine
│   └── RandomNumberGenerator.h   # RNG wrapper (RAII)
├── src/
│   ├── EuropeanOption.cpp
│   ├── BlackScholes.cpp
│   ├── MonteCarloPricer.cpp
│   ├── RandomNumberGenerator.cpp
│   └── main.cpp                  # Demo with convergence study
└── tests/
    └── test_pricer.cpp           # 13 unit tests
```

## Build & Run

```bash
mkdir build && cd build
cmake ..
make -j4
./mc_pricer      # Run the pricer demo
./tests          # Run unit tests
```

## Finance Background

The pricer implements risk-neutral Monte Carlo pricing:

1. **Geometric Brownian Motion**: S_T = S₀ · exp((r - σ²/2)T + σ√T · Z)
2. **Risk-Neutral Pricing**: V = e^(-rT) · E[payoff(S_T)]
3. **Error Scaling**: Standard error ∝ 1/√N (Central Limit Theorem)

The Black-Scholes analytical solution serves as the validation reference — analogous to comparing a Monte Carlo event generator against a known cross-section in particle physics.

## Next Steps (Intermediate Version)

- [ ] Greeks (Delta, Gamma, Vega, Theta) via bump-and-revalue
- [ ] Variance reduction: antithetic variates, control variates
- [ ] Exotic options: Asian, Barrier
- [ ] Multithreading with `std::thread` / `std::async`
- [ ] Yield curve term structure
- [ ] Google Test integration

## Author

Built as part of a 12-month HEP → Quant Finance transition plan.
