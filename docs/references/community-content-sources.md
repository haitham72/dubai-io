# Community fixture sources and editorial notes

The community and chat records in this pass are fictional demo content. Persona names, handles, relationships, and conversations were authored for Dubai-io; they do not represent Reddit users or real people. Topics were informed by recurring question patterns in public Dubai forums: moving and rent tradeoffs, job-listing transparency, used-item listings, school-run logistics, and small-business advice.

Research references used for topic direction:

- [r/DubaiCentral relocation discussion](https://www.reddit.com/r/DubaiCentral/comments/1qtshar/relocating_soon_to_dubai/) — relocation timing, apartment search, and job-search uncertainty.
- [r/UAE moving discussion](https://www.reddit.com/r/UAE/comments/1dbhugp/moving_to_dubai/) — rent, employment, and household decision tradeoffs.
- [r/dubai apartment search discussion](https://www.reddit.com/r/dubai/comments/1kkowyc) — commute and temporary-housing questions.
- [r/dubai jobs discussion](https://www.reddit.com/r/dubai/comments/1l6ybzc) — job-market uncertainty and realistic expectations.
- [r/DubaiJobs topic overview](https://gummysearch.com/r/DubaiJobs/) — common themes such as hiring posts, salary ranges, CV advice, and visa context.

No post text, username, avatar, or identifying detail was copied. The fixture prose is original and uses the references only for topic selection and conversational tone.

## Image references

Avatars in both `apps/api/app/fixtures/community/personas.json` and `apps/api/app/fixtures/chat_personas.json` use direct `images.unsplash.com` asset URLs with `w=160&h=160&fit=crop&auto=format` parameters. Each profile carries `avatar_source` with the direct Unsplash asset ID, provider, license label, and access date. They are remote references for the prototype and should be downloaded into an approved, licensed asset bucket with attribution before production. Community cards use the repository's existing `media/*.jpg` demo assets so offline fixture loading remains deterministic.

## Fixture contract

`chat_personas.json` has `personas[]` and `threads[]`. Each message has a `persona_id` (or `null` for the current user), and each thread's `persona_ids` declares the participating profiles. Community comments may include a stable `id` and `parent_id`; for seeded records the ID format is `<post-id>-cNN`. A null parent is a direct reply to the post. This supports nested Reddit-style rendering while remaining backward-compatible with the existing loader.

All records are marked by the loader as `demo_fixture`; they must never be presented as verified local facts or as real user statements.
