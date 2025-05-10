These are some general things to keep in mind while doing development work on this project:

- This is a general-purpose framework, and so all solutions implemented must be workflow-agnostic. We should not implement and custom or special handling for specific workflow instances. What this means in practice is that the workflow engine can make special allowances for specific utilities by referencing the node's function, but not make any special allowances for a node as referenced by its id.

- A step node does not have to have a defined utility. If there is no defined utility, we continue as if there was a utility function and it executed successfully. 

- A next relationship doesn't need to have a condition or operator defined. If these things do not exist, we assume the path should be followed. The only time a next relationship (aka. path) isn't followed is when the function involving it's conditions list and operator returns false. 

- The project implements a variable handling system that enables loops to be designed. Endless loops can be an intentionally designed function of this system representing an endless conversation.

- We've had consistent issues in this project with property mismatches between "function" and "utility" as the key. Keep an eye out for this and remember that it's actually "function" on the read nodes in the graph.