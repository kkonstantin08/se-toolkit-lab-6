# Task 1: Call an LLM from Code — Implementation Plan

## 1. Objective
Build a CLI agent that can answer questions by calling a Large Language Model (LLM) programmatically.

## 2. Requirements Analysis

### Core Features
- [ ] Create a CLI interface for user interaction
- [ ] Implement LLM API integration (OpenAI or compatible)
- [ ] Add tool: File reader (to read lab documentation)
- [ ] Add tool: Backend API query tool
- [ ] Enable agent to answer questions using available tools

### Technical Requirements
- [ ] Python-based implementation
- [ ] Proper error handling for API calls
- [ ] Logging and debugging capabilities
- [ ] Test coverage for all components

## 3. Implementation Steps

### Phase 1: Setup
- [ ] Set up development environment
- [ ] Configure LLM API credentials (provider details described in `.env.secret.agent`)
- [ ] Create project structure

### Phase 2: Core Implementation
- [ ] Implement LLM client wrapper
- [ ] Build CLI interface
- [ ] Create tool abstraction layer

### Phase 3: Tools Development
- [ ] Implement file reading tool
- [ ] Implement API query tool
- [ ] Test each tool independently

### Phase 4: Integration & Testing
- [ ] Integrate tools with agent
- [ ] Run test cases
- [ ] Fix bugs and iterate


## 5. Success Criteria
- [ ] Agent passes all automated tests
- [ ] Agent can answer questions about lab documentation
- [ ] Agent can query backend API successfully
- [ ] Code is well-documented and maintainable

## 6. Timeline
| Phase | Estimated Time | Status |
|-------|---------------|--------|
| Setup | 1-2 hours | ⬜ Not Started |
| Core Implementation | 3-4 hours | ⬜ Not Started |
| Tools Development | 2-3 hours | ⬜ Not Started |
| Testing & Iteration | 2-3 hours | ⬜ Not Started |

## 7. Notes & Blockers
- [ ] LLM provider configuration is described in `.env.secret.agent`
- [ ] Sync fork with upstream regularly
- [ ] Review lab documentation for specific requirements

## 8. Resources
- Task description: `lab/tasks/required/task-1.md`
- LLM API documentation
- Lab repository: `inno-se-toolkit/se-toolkit-lab-6`
- Configuration file: `.env.secret.agent`
