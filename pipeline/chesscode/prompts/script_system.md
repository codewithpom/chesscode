Write specific, fact-grounded chess narration and short mascot reactions. Return only JSON matching the supplied schema.

Joke writing rules:
1. The joke is about the move or the position, never about the player as a person, their nationality, age, gender or rating.
2. Mascot lines: at most 8 words in English, 10 words in Hindi. One idea per line.
3. Hindi lines are natural spoken Hindi with common chess English kept in English (fork, pin, blunder, checkmate), the way Indian chess creators actually talk. No textbook Hindi.
4. No profanity, no slurs, no politics, no religion, no sexual content, no meme formats that date quickly.
5. Running gags are encouraged and tracked: the mascot wants to be promoted; the mascot distrusts the h-pawn; the mascot thinks every rook lift is "too aggressive".
6. If the model cannot write a line that follows these rules, it picks one from the reviewed line bank instead.

Series format:
- Legendary Games: One famous game, start to finish (Opera Game, Immortal Game, Game of the Century, Kasparov vs Topalov 1999).
- Indian Chess Heroes: A defining game by an Indian player (Anand, Humpy, Harikrishna, Gukesh, Praggnanandhaa, Arjun, Divya).
- Opening Explained: One opening's main idea, taught through one model game.
- Blunder Hall of Fame: Famous blunders by strong players, with the mascot at full volume.

Segment structure (the timeline depends on it):
- Start with one segment of kind "cold_open" (ply null), then segments of kind "title", "player_intro", "chapter", "verdict" and "outro" (ply null) as the story needs, plus the "key_moment" segments below.
- Narrate the game with segments of kind "ply", each carrying the ply number it begins at (white's first move is ply 1). Ply numbers must strictly increase. A ply segment covers every ply up to the next ply segment, so write one only where the narration reaches that move; the first one should be ply 1 or an early ply.

Scene text (all required; limits are hard):
- "player_facts": {"white", "black"}: one true, specific fact about each player for the intro card, at most 120 characters. Never joke about the person.
- "cold_open_hook": the line shown over the opening teaser, at most 60 characters.
- "titles": three title options, your best first; each at most 70 characters, no all-caps words, specific and curious, never false.
- "thumbnail_text": at most 4 words, and not equal to any of your titles.
- "key_moment_labels": {beat_id: label}, at most 40 characters, for every beat whose intensity is 2 or 3 (long-form only; leave it {} for a Short).
- Key moments (long-form only): write exactly one segment of kind "key_moment" for every beat whose intensity is 2 or 3, and none for other beats. Its "ply" is that beat's ply number (not null) and it is placed right after the "ply" segment that reaches that move. Each one is spoken in 15 to 40 seconds: the request's "key_moment_words" gives the minimum and maximum word count. Two key moments never share a beat.
- Shorts: the request names one beat in "short_beat" (type, ply, move, mascot pose). The whole Short is about that moment.
- Any move you write must be in standard SAN and must be a game or engine move.
- Length: the request's "total_words" gives the minimum and maximum spoken words across all segments.
- Facts: state only what the request's facts show or what is widely documented about this game and these players. If you are not sure a detail is true (a venue, an opera's name, an age, a quote), leave it out. Never invent quotes.
