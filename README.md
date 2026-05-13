# new_svi_crawler

`new_svi_crawler` 是一个 AOI 驱动的街景图像采集系统，使用 Scrapy、Redis、MySQL 和 Docker Compose 构建。系统接收目标区域文件，生成采样点，发现街景 panoid，持久化街景元数据，并通过独立的 pano worker 下载和拼接全景图像。

项目将轻量 HTTP 元数据抓取和较重的图像处理拆开。Scrapy 负责 seed 和 metadata 请求；Redis 负责在 crawler 与 pano worker 之间传递图片任务；MySQL 保存 job 状态、seed 状态、pano 元数据、全景图文件记录和错误信息。

## 架构

```text
AOI GeoJSON
  -> seed point generator
  -> Scrapy StreetviewSpider
  -> seed API
  -> metadata API
  -> StreetviewPipeline
  -> MySQL pano
  -> Redis pano_download_queue
  -> pano worker
  -> stitched panorama image
  -> MySQL pano_file
```

主要组件：

- `StreetviewSpider`：创建 seed / metadata API 的 Scrapy Request，解析 JSON 响应，并产出 Item。
- `StreetviewPipeline`：将 `SeedTaskItem`、`PanoItem`、`CrawlErrorItem` 写入 MySQL，并将图片任务推入 Redis。
- `RedisPanoDownloadQueue`：管理每个 job 对应的 `pano_download_queue`、`pano_download_seen` 和 `metadata_done`。
- `pano_worker`：消费 Redis 图片任务，下载瓦片，拼接全景图，写入图片文件和处理状态。
- `MySQLRepository`：封装持久化写入、幂等更新和恢复查询。
- `cli`：创建或恢复 job，并协调 Scrapy spider 和 pano worker 的生命周期。

## 数据模型

MySQL 初始化脚本位于 `docker/mysql/init/001_schema.sql`。

| 表 | 作用 |
| --- | --- |
| `crawl_job` | 记录一次采集任务的状态和配置路径 |
| `seed_task` | 记录 AOI 采样点和 seed API 处理状态 |
| `pano` | 保存已确认的街景元数据，包括结构化字段和完整 `raw_json` |
| `pano_file` | 保存全景图文件路径、尺寸、大小、SHA256 和处理状态 |
| `crawl_error` | 保存 seed、metadata、pano_download 阶段的错误记录 |

MySQL 是系统的事实来源。Redis 队列可以在恢复任务时从 MySQL 状态重建。

## Redis key

每个 job 使用独立 Redis key：

```text
streetview:{job_id}:pano_download_queue
streetview:{job_id}:pano_download_seen
streetview:{job_id}:metadata_done
```

`pano_download_seen` 使用下面的 pano file identity 去重：

```text
{panoid}:{file_type}:{file_spec}
```

默认全景图任务为：

```text
file_type = panorama
file_spec = full
```

## 安装

创建虚拟环境并安装项目：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
```

启动 MySQL 和 Redis：

```powershell
docker compose up -d mysql redis
```

运行测试：

```powershell
.\.venv\Scripts\python -m pytest -q
```

## 配置

默认配置文件为 `configs/base.yaml`。

关键字段：

```yaml
aoi_path: inputs/sample_aoi.geojson
sample_interval_m: 50
output_dir: data/images
report_dir: data/reports

crawler:
  provider: baidu
  timeout_seconds: 10
  retry_times: 3
  concurrency: 16

pano_file:
  enabled: true
  workers: 2
  file_type: panorama
  file_spec: full
  tile_zoom: 4
  tile_cols: 4
  tile_rows: 2
```

接口地址和字段解析集中在下面两个模块中：

- `src/streetview_crawler/providers/baidu.py`
- `src/streetview_crawler/svi_processing/downloader.py`
- `src/streetview_crawler/svi_processing/stitcher.py`

数据库和 Redis 连接通过环境变量读取：

```text
MYSQL_HOST
MYSQL_PORT
MYSQL_USER
MYSQL_PASSWORD
MYSQL_DATABASE
REDIS_HOST
REDIS_PORT
```

在 Docker Compose 中，crawler 容器应通过服务名访问依赖：

```text
MYSQL_HOST=mysql
REDIS_HOST=redis
```

## 运行任务

创建新任务：

```powershell
.\.venv\Scripts\python -m streetview_crawler.cli run-job --config configs/base.yaml
```

恢复已有任务：

```powershell
.\.venv\Scripts\python -m streetview_crawler.cli resume-job --job-id <job_id> --config configs/base.yaml
```

通过 Docker 运行：

```powershell
docker compose run --rm crawler python -m streetview_crawler.cli run-job --config configs/base.yaml
```

## 输出

全景图像：

```text
data/images/{job_id}/{panoid}.jpg
```

运行报告：

```text
data/reports/{job_id}/run_report.json
data/reports/{job_id}/run_summary.md
```

## 恢复机制

恢复逻辑基于 MySQL 状态：

- `seed_task.status IN ('pending', 'failed')` 表示需要补跑 seed API。
- `seed_task.status = 'found'` 但 `pano` 表没有对应记录，表示需要补跑 metadata API。
- `pano` 已存在但没有成功的 `pano_file`，表示需要重新生成 Redis pano download task。

Redis 不作为持久调度状态。恢复任务时，可以清空 Redis pano 下载相关 key，再根据 MySQL 查询结果重建队列。

## 开发检查

常用检查命令：

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m compileall src tests
$env:PYTHONPATH='src'; python -m scrapy list
docker compose config --quiet
```

当前测试覆盖 seed point 生成、metadata 字段提取、Redis queue 去重、图片拼接和 SHA256 计算。
