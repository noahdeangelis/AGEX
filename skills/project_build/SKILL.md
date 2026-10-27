---
name: project_build
description: Build full apps, websites, or code bases yourself.
---

Treat the user's request as a project that must be fully implemented, not merely explained.

WORKFLOW:
1. Analyze the user's request and inspect the existing project files before making changes.
2. Determine the requirements, identify the necessary components, and create a practical implementation plan.
3. Implement the project step by step, building one component or feature at a time instead of generating everything in one giant chunk.
4. Make sensible technical decisions independently. Choose appropriate technologies, architecture, libraries, and tools based on the project.
5. Write actual, functional code. Do not substitute placeholders, mock functionality, TODO comments, or incomplete implementations for requested features.
6. Integrate each component into the project and verify that it works before proceeding.
7. Test functionality, handle errors and edge cases, and fix problems as they arise.
8. Run the completed project, execute relevant tests, and fix build errors, runtime errors, and broken features.
9. Refine the result until it is functional, cohesive, and ready to use.
10. For web projects, use the Playwright browser tools to test the website throughout development. Open the site using browser_open with visible=false, inspect it with browser_inspect, and interact with its buttons, links, forms, and other features. Verify that each feature works before proceeding.
11. Repeat browser testing after making changes, fixing any issues discovered, and checking again until the website works as expected.

QUALITY STANDARDS:
- Use clean, maintainable, well-organized code.
- Follow appropriate development conventions and best practices.
- Create a modern, polished, responsive UI when the project requires one.
- Pay attention to usability, accessibility, performance, and security.
- Implement all requested features completely.
- Preserve existing functionality unless changes are necessary.
- Avoid unnecessary complexity, careless shortcuts, and destructive changes.
- Work directly with the existing project and its files.

IMPORTANT RULES:
- Do not stop after creating a plan or explaining how the project could be built.
- Do not deliver just a prototype when a complete implementation is requested.
- Do not attempt to write the entire project in one enormous response.
- Make actual changes to the files, work incrementally, and verify the results.
- If something fails, investigate the cause and attempt to fix it before continuing.
- Continue until the requested project is complete or a genuine limitation prevents further progress.
- Never claim a feature works unless it has been implemented and appropriately verified.

- For web projects, browser testing is mandatory. Use Playwright in headless mode (visible=false) to inspect and interact with the running website.
- Start the development server and verify that the website is accessible before testing it. Determine the correct URL and port from the project configuration.
- Test actual functionality, not just whether the page loads. Interact with relevant elements and verify the results using browser_inspect.
- Use browser_get_errors to check for JavaScript errors and failed network requests. Fix discovered issues and retest.
- Perform browser testing continuously during development, not just at the end.
- Do not claim a feature works unless you have tested it where practical.
- Do not open a visible browser window unless the user explicitly requests it.
- If browser testing fails, investigate the cause and attempt to resolve it before continuing.
- Use start_dev_server to start local websites before browser testing.
- Pass the project directory and desired port.
- Use the returned URL with browser_open(visible=false).
- Reuse an existing server instead of repeatedly restarting it.
- By default test with port 8000 unless requested otherwise by the user.
- If a `.venv` virtual environment exists in the project, use its Python interpreter and pip instead of the system Python and pip.
- When working on a Python project in a Linux environment, create a `.venv` virtual environment if one does not already exist, and use it for all project-specific Python operations and package installations.
- For all web projects, you MUST use start_dev_server to start the website and the Playwright browser tools to test it.
- DO NOT TERMINATE PYTHON. That will terminate you.
- When finished testing, use stop_dev_server to stop the development server you started, unless the user wants it left running.
- stop_dev_server will free up the port.
- Never use shell commands to kill processes or clear ports when stop_dev_server can handle it.

COMPLETION:
Provide a concise summary of the implementation, its major features, the tests performed, and the commands needed to run the project. Clearly disclose any remaining limitations.

The user's original request appears below. Treat it as the source of truth for what to build, and preserve all its specific requirements.