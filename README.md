# sumo-hooks
### Sumo data parsing exercise using Flask and sumo-api.com webhooks

- Receiving subscribed requests for newMatches ~4am EST from sumo-api.com
- For new matches every day, compile and format (discord code block) the div.1 named bouts (makuuchi)
- Save and append to history of previous match data
- Get basho year/date from newmatches updates rather than statically
