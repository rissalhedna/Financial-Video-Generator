# Prompts Library

This folder contains all prompts used by the agentic script generation pipeline.

## Pipeline Flow

```
Introduction → Development → Charts → Conclusion → Revision → Visual Mapper
```

## Prompt Files

| File                                 | Agent             | Duration | Purpose                      |
| ------------------------------------ | ----------------- | -------- | ---------------------------- |
| [introduction.md](introduction.md)   | IntroductionAgent | 10-20s   | Hook to capture attention    |
| [development.md](development.md)     | DevelopmentAgent  | 10-20s   | Key facts and context        |
| [charts.md](charts.md)               | ChartsAgent       | ~10s     | Data visualization segment   |
| [conclusion.md](conclusion.md)       | ConclusionAgent   | 10-20s   | Story close                  |
| [revision.md](revision.md)           | RevisionAgent     | -        | Consistency check            |
| [visual_mapper.md](visual_mapper.md) | VisualMapperAgent | -        | Add emotions, tags, triggers |

## Shared Rules

All prompts enforce these rules:

- No investment advice
- Educational tone only
- No listing items ("phones, tablets, watches...")
- Social media style
- Natural, conversational language

## Modifying Prompts

1. Edit the markdown file in this folder
2. Update the corresponding agent in `app/agents/`
3. Test with: `python -m app.generate --topic "Test Topic"`
