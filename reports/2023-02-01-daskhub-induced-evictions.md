# 2023-02-01 Heavy use of dask-gateway induced critical pod evictions

## Timeline

All times in UTC+1

- 2023-02-01 - [Summary of issue updated between ~8-9 PM](https://github.com/2i2c-org/infrastructure/issues/2126#issuecomment-1412554908)

## What went wrong

- I believe various critical pods on core nodes pods got evicted when prometheus started scraping from ~200 nodes metrics exporters
- I think its likely, but I can't say for sure, that the dask scheduler pod also would run into resource limitations with this amount of workers

## Follow-up improvements

- #2127
- #2213
- #2209 
- #2324
- #2366
