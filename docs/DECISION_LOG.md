# Decision Log

## Monorepo Choice
**Date**: 2024-10-25  
**Decision**: Adoption of the monorepo approach  
**Rationale**:
- Simplification of code management
- More efficient handling of shared dependencies
- Increased development efficiency
- The exam task assumes implementation within a single repository

---

## Dummy Service Programming Language Choice
**Date**: 2024-10-25  
**Decision**: Implementation of the Dummy Service in Python  
**Rationale**:
- **Simplicity**: Python has an easily understandable syntax, allowing for rapid development.
- **Rich library ecosystem**: There are many built-in and third-party libraries available to assist with data handling and REST API creation.
- **Widely used**: Python's popularity ensures good community support, making it easy to find resources or help when needed.

---

## Gateway Service Programming Language Choice
**Date**: 2024-10-25  
**Decision**: Implementation of the Gateway Service in Node.js  
**Rationale**:
- **Asynchronous operation**: Node.js uses an asynchronous I/O model, which helps in efficiently handling high traffic requests, making it ideal for the Gateway Service.
- **Easy REST API creation**: There are many popular frameworks available for Node.js, such as Express.js, which simplify the creation and management of API endpoints.

---

## Gateway Service Programming Language Choice change
**Date**: 2024-10-26  
**Decision**: Implementation of the Gateway Service in Python  
**Rationale**:
- **Consistent language environment**: Using Python for both the Dummy Service and Gateway simplifies the overall environment, which can streamline development and reduce setup complexity.
- **Skill assessment relevance**: Given that the purpose of this implementation is partly to assess DevOps programming skills, Python provides a better basis for evaluation due to its straightforward syntax and wide applicability in DevOps tasks.
- **Comparable learning needs**: While Node.js could offer advantages for asynchronous handling, Python is chosen as it meets the same requirements with a similar learning curve in this context.
  
```