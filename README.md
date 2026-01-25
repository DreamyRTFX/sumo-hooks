# sumo-hooks
### Sumo data parsing exercise using Flask and sumo-api.com webhooks

- Receiving subscribed requests for newMatches ~4am EST from sumo-api.com
- For new matches every day, compile and format (discord code block) the div.1 named bouts (makuuchi)
- Save and append to history of previous match data
- Get basho year/date from newmatches updates rather than statically


TODO

- clean up extra titles
- schedule for later (avoid spoilers)











- ETL Extract transform load (newmatches->get request->transform/visualise)
    ->report at the end
    store in json, store key(day/date)

- batch job 
    executes on time basis
    eg. store on disk, cron job

- persistent im memory
    async sleep

Model view controller