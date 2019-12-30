# Design Document for Empires Online

## Entities

* Country
  * id
  * default_gold
  * default_bonds
  * default_territories
  * default_goods
  * default_people

* Player
  * id
  * username
  * password
  * email
  * email_verification_code
  * spawned_country_id

* Spawned_Country
  * id
  * country_id
  * game_id
  * gold
  * bonds
  * territories
  * goods
  * people
  * banks 

* Game
  * id
  * rounds
  * rounds_remaining
  * phase
  * creator_id
  * creation_date

Examples:

Country

|id|name|default_gold|default_bonds|default_territories|default_goods|default_people|
|---|-------|--------|-----|-----------------------|------------------|---|
| 4 | France | 5  | 1 | 4   | 2   | 3



Player

|id|username|password|email|email_verification|spawned-country-id|
|---|-------|--------|-----|-----------------------|------------------|
| 1 | Roger | 12345  | roger@gmail.com | abcdefg   | 1                |

Spawned Country

| id  | country_id  | game_id  | gold | bonds  | terrirtories | goods  | people  | banks  | supporters | revolters |
|---|---|---|---|---|---|---|---|---|---|---|
| 1  | 4  | 1  |  5 | 1  |  4 | 2  | 3  | 0  | 0 | 0

Game

|id|rounds|rounds_remaining|phase|creator_id|creation_date
|---|-------|--------|-----|-----------------------|------------------|
| 1 | 5 | 5  |  1 | 1 | 2019-12-30 22:17:10


## EndPoints

Develop pseudo-logic:

```
luxuries=MIN(people,goods)
industries=MIN(territories,people-luxuries)
unemployed=people-luxuries-industries
if unemployed > 1 then set revolt=revolt+1

set revolt=revolt+(bonds-banks)
and
set gold=gold-banks
and
set supporters=supporters+luxuries
and
goods=MIN(territories,people)
```

example
```
4 gold
1 bond / 1 bank 
2 goods
4 territories
3 people
0 supporters
0 revolt
```

```
luxuries=MIN(people,goods) // output 2

industries=MIN(territories,people-luxuries) // compare 4 with (3-2). gives 1 industry
unemployed=people-luxuries-industries // zero unemployed
if unemployed > 1 then set revolt=revolt+1 // zero revolt

set revolt=revolt+(bonds-banks) // no more revolt
and
set gold=gold-banks // gold is now 3 instead of 4
and
set supporters=supporters+luxuries // supporters is now 2
and
goods=MIN(territories,people) // goods is now 3
```





