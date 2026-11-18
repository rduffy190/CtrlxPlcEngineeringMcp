# Acknowledgements

## Use of AI in this software

Parts of this software were generated and tested with the help of Anthropic's AI models **Claude Opus 5.5** and
**Claude Sonnet 5.5**, working in Claude Code under the direction of the author.

What that covers:

- **Code:** much of the MCP server (`server/`), the IDE bridge (`bridge/`), the Windows setup scripts (`scripts/`)
  and the example projects (`examples/`) was written or revised by the models from the author's requests.
- **Documentation:** the README and this file were drafted or edited with the models.
- **Testing:** the models wrote and ran tests (`tests/`), ran the tools against ctrlX PLC Engineering and its
  simulator, and helped investigate and fix the problems that turned up.

The author set the requirements, directed the work, ran it on real ctrlX PLC Engineering installations and
decided what was kept. AI-assisted work can still contain mistakes. Review the code before you rely on it, and
test on a simulator before you use it on a machine that can move or hurt something. The tools can log in to,
start, stop and write to a controller. See the [Rules for the agent](README.md#rules-for-the-agent) and the
test coverage notes in the README for what has and has not been exercised.

## Other software

This project builds on the Model Context Protocol Python SDK (`mcp`), on the CODESYS Scripting Engine that ships
with ctrlX PLC Engineering, and on the author's ctrlX skill repositories listed under
[Required skills](README.md#required-skills-ladder-and-hmi-tools). ctrlX, ctrlX CORE and ctrlX PLC Engineering are
products of Bosch Rexroth, and CODESYS is a product of CODESYS GmbH. This project is independent and is not
affiliated with or endorsed by either, or by Anthropic.

No ctrlX PLC Engineering or CODESYS content is shipped in this repository. Where the tools need a real object to
start from (a trace, a Web Visualization), they copy one from the user's own project, and the HMI templates of the
ctrlx-hmi skill are made by each user from their own ctrlX PLC Engineering.

The software is provided under the MIT License, see [LICENSE](LICENSE), without warranty of any kind.
