import json
import requests
from datetime import datetime, timedelta
import sys
import tkinter as tk
from tkinter import messagebox

class SilentCarouselGenerator:
    def __init__(self, config_file="config.json"):
        # 初始化类，设置配置文件路径和默认值
        self.config_file = config_file  # 配置文件路径，默认为 config.json
        self.EMBY_SERVER = ""  # Emby 服务器地址
        self.EMBY_API_KEY = ""  # Emby API 密钥
        self.descriptions = {  # 预定义的描述和提示，用于不同标签页
            1: (
                "这是一份温暖的陪伴，也是每天的新鲜惊喜。...",  # 每日电影描述
                "DAILY MOVIE"  # 每日电影提示
            ),
            2: (
                "探索“最新电影”的璀璨星辰！...",  # 新上映电影描述
                "NEW RELEASES"  # 新上映提示
            ),
            3: (
                "这是您掌握电视剧新潮流，及时追新的必选之地。...",  # 近期剧集描述
                "RECENT SERIES"  # 近期剧集提示
            ),
            4: (
                "这是您探索电影系列世界的优选之地。...",  # 电影合集描述
                "FILM COLLECTION"  # 电影合集提示
            )
        }
        self.load_config()  # 加载配置文件

    def load_config(self):
        """加载 config.json 配置文件"""
        try:
            # 打开并读取 config.json 文件
            with open(self.config_file, "r", encoding="utf-8-sig") as f:
                config = json.load(f)
                # 打印加载的配置内容（用于调试）
                print(f"Loaded config: {json.dumps(config, indent=2, ensure_ascii=False)}")
                # 获取 Emby 服务器地址并确保以 '/' 结尾
                self.EMBY_SERVER = config.get("EMBY_SERVER", "").rstrip("/") + "/"
                # 获取 Emby API 密钥
                self.EMBY_API_KEY = config.get("EMBY_API_KEY", "")
                # 获取标签页配置，默认为空列表
                self.tabs = config.get("tabs", [])
                # 检查 Emby 服务器地址和 API 密钥是否为空
                if not self.EMBY_SERVER or not self.EMBY_API_KEY:
                    raise ValueError("EMBY_SERVER or EMBY_API_KEY missing in config")
                # 如果 tabs 为空，打印警告
                if not self.tabs:
                    print("警告：配置文件中 'tabs' 为空或缺失")
        except FileNotFoundError:
            # 如果配置文件不存在，打印错误并显示弹窗
            print(f"错误：未找到配置文件 '{self.config_file}'")
            self.show_error_popup("未找到配置文件。请先使用GUI版本保存配置。")
            sys.exit(1)
        except json.JSONDecodeError as e:
            # 如果 JSON 格式错误，打印错误并显示弹窗
            print(f"错误：'{self.config_file}' 中的 JSON 格式无效：{e}")
            self.show_error_popup("配置文件 JSON 格式无效。请先使用GUI版本保存有效配置。")
            sys.exit(1)
        except Exception as e:
            # 其他加载配置的错误，打印错误并显示弹窗
            print(f"错误：加载配置失败：{e}")
            self.show_error_popup(f"加载配置文件失败：{e}。请先使用GUI版本保存配置。")
            sys.exit(1)

    def show_error_popup(self, message):
        """在打包为 exe 时显示错误弹窗"""
        # 检查是否以可执行文件形式运行（由 PyInstaller 等工具设置）
        if getattr(sys, 'frozen', False):
            root = tk.Tk()  # 创建 Tkinter 窗口
            root.withdraw()  # 隐藏主窗口
            # 显示错误弹窗，包含自定义消息和提示
            messagebox.showerror("配置错误", f"{message}\n请先用GUI版本保存一次配置后再运行此程序")
            root.destroy()  # 销毁窗口

    def get_movies(self, params, limit, retain_count, default_overview, tips, check_run_time_ticks=True):
        """从 Emby 服务器获取电影数据"""
        try:
            # 发送 GET 请求到 Emby 服务器获取电影数据
            response = requests.get(f"{self.EMBY_SERVER}emby/Items", params=params, timeout=10)
            response.raise_for_status()  # 检查请求是否成功
            movies_pc = []  # 存储电影数据
            previous_movie_title = None  # 上一个电影标题，用于去重
            previous_run_time_ticks = None  # 上一个电影运行时间，用于去重
            run_time_ticks_set = set()  # 存储已处理的运行时间

            # 遍历返回的电影数据
            for item in response.json().get("Items", []):
                run_time_ticks = None
                if check_run_time_ticks:
                    # 获取电影运行时间（用于去重）
                    run_time_ticks = item.get("RunTimeTicks")
                    if run_time_ticks in run_time_ticks_set:
                        print(f"跳过重复电影：{item['Name']}")
                        continue
                    if run_time_ticks == previous_run_time_ticks:
                        continue

                title = item.get("Name", "")  # 获取电影标题
                run_time_ticks_set.add(run_time_ticks)  # 添加运行时间到集合

                # 构造电影的图片 URL
                image_url1 = f"{self.EMBY_SERVER}emby/Items/{item['Id']}/Images/Backdrop"
                image_url2 = f"{self.EMBY_SERVER}emby/Items/{item['Id']}/Images/Primary"
                image_url3 = f"{self.EMBY_SERVER}emby/Items/{item['Id']}/Images/Logo"

                # 验证图片 URL 是否存在（可选，提高可靠性）
                for url in [image_url1, image_url2, image_url3]:
                    try:
                        img_response = requests.head(url, timeout=5)
                        if img_response.status_code != 200:
                            print(f"警告：图片未找到：{url}")
                    except requests.RequestException:
                        print(f"警告：无法验证图片：{url}")

                # 构造电影数据字典
                movie_pc = {
                    "display": "image",
                    "link": image_url1,
                    "title": title,
                    "description": item.get("Overview", default_overview).replace('"', ''),
                    "thumb": image_url2,
                    "url": "#",
                    "alt": item["Id"],
                    "tips": tips,
                    "logo": image_url3,
                }

                # 跳过标题重复的电影
                if movie_pc["title"] == previous_movie_title:
                    print(f"跳过重复电影：{movie_pc['title']}")
                    continue

                movies_pc.append(movie_pc)  # 添加电影到列表
                previous_movie_title = movie_pc["title"]  # 更新上一个标题
                previous_run_time_ticks = run_time_ticks  # 更新上一个运行时间
                if len(movies_pc) == limit:  # 达到限制数量时停止
                    break

            return movies_pc[:retain_count]  # 返回指定数量的电影
        except requests.RequestException as e:
            # 网络请求错误
            print(f"错误：获取电影失败：{e}")
            return []
        except Exception as e:
            # 其他处理电影数据的错误
            print(f"错误：处理电影数据失败：{e}")
            return []

    def generate_carousel(self):
        """生成轮播数据并保存到 data_pc.js"""
        all_results = []  # 存储所有轮播数据
        has_selected_parent_id = False  # 标记是否有有效的 selected_parent_ids

        # 遍历配置中的所有标签页
        for index, tab in enumerate(self.tabs):
            if not tab.get("enabled", True):
                # 跳过禁用的标签页
                print(f"跳过禁用的标签页：{tab.get('tab_name', 'Unknown')}")
                continue

            # 获取 result_retain_count
            try:
                result_retain_count = int(tab.get("result_retain_count", "1"))
            except ValueError:
                print(f"错误：标签页 '{tab.get('tab_name', 'Unknown')}' 的 result_retain_count 无效：{tab.get('result_retain_count')}")
                continue

            # 获取 retain_count
            try:
                retain_count = int(tab.get("retain_count", "1"))
            except ValueError:
                print(f"错误：标签页 '{tab.get('tab_name', 'Unknown')}' 的 retain_count 无效：{tab.get('retain_count')}")
                continue

            limit = retain_count * 2  # 设置请求限制数量
            selected_parent_ids = tab.get("selected_parent_ids", [])  # 获取父 ID 列表
            if selected_parent_ids:
                has_selected_parent_id = True  # 标记找到有效的父 ID
            else:
                print(f"警告：标签页 '{tab.get('tab_name', 'Unknown')}' 没有 selected_parent_ids")
                continue

            recursive = tab.get("recursive", True)  # 是否递归查询，默认为 True
            sort_by = tab.get("sort_by", "Random")  # 排序方式，默认为随机
            sort_order = tab.get("sort_order", "Ascending")  # 排序顺序，默认为升序
            include_item_type = tab.get("include_item_type", "Movie")  # 包含的条目类型，默认为 Movie
            # 处理优先电影列表
            priority_movies = [m.strip() for m in tab.get("priority_movies", "").split(",") if m.strip()]
            min_premiere_days = tab.get("min_premiere_days", "")  # 最小首映天数

            # 验证 include_item_type
            if include_item_type not in ["Movie", "Series", "BoxSet"]:
                print(f"警告：标签页 '{tab.get('tab_name', 'Unknown')}' 的 include_item_type 无效 '{include_item_type}'，默认使用 'Movie'")
                include_item_type = "Movie"

            # 处理 min_premiere_days
            min_premiere_date = None
            if min_premiere_days:
                try:
                    min_premiere_days = int(min_premiere_days)
                    min_premiere_date = (datetime.now() - timedelta(days=min_premiere_days)).isoformat()
                except ValueError:
                    print(f"错误：标签页 '{tab.get('tab_name', 'Unknown')}' 的 min_premiere_days 无效：{min_premiere_days}")
                    continue

            # 获取描述和提示
            tab_index = index + 1
            if tab_index in self.descriptions:
                description, tips = self.descriptions[tab_index]
            else:
                description = "这是您探索电影系列世界的优选之地。..."  # 默认描述
                tips = "CUSTOM COLLECTION"  # 默认提示

            tab_movies_pc = []  # 存储普通电影
            priority_movies_pc = []  # 存储优先电影

            # 遍历所有父 ID
            for parent_id in selected_parent_ids:
                # 获取优先电影
                for priority_movie in priority_movies:
                    params = {
                        "Limit": limit,
                        "ParentId": parent_id,
                        "Recursive": recursive,
                        "Fields": "Overview",
                        "SortBy": sort_by,
                        "SortOrder": sort_order,
                        "IncludeItemTypes": include_item_type,
                        "api_key": self.EMBY_API_KEY,
                        "NameStartsWith": priority_movie
                    }
                    if min_premiere_date:
                        params["MinPremiereDate"] = min_premiere_date

                    print(f"获取优先电影 '{priority_movie}'，父 ID：{parent_id}")
                    collection_pc = self.get_movies(
                        params,
                        limit,
                        retain_count,
                        description,
                        tips,
                        check_run_time_ticks=False
                    )
                    print(f"获取到 {len(collection_pc)} 个优先电影项目：'{priority_movie}'")
                    for movie in collection_pc:
                        if priority_movie.lower() in movie["title"].lower():
                            priority_movies_pc.append(movie)
                            print(f"匹配到优先电影：{movie['title']}")

                # 获取普通电影
                params = {
                    "Limit": limit,
                    "ParentId": parent_id,
                    "Recursive": recursive,
                    "Fields": "Overview",
                    "SortBy": sort_by,
                    "SortOrder": sort_order,
                    "IncludeItemTypes": include_item_type,
                    "api_key": self.EMBY_API_KEY
                }
                if min_premiere_date:
                    params["MinPremiereDate"] = min_premiere_date

                print(f"获取普通电影，父 ID：{parent_id}")
                collection_pc = self.get_movies(
                    params,
                    limit,
                    retain_count,
                    description,
                    tips,
                    check_run_time_ticks=False
                )
                print(f"获取到 {len(collection_pc)} 个普通电影项目")
                for movie in collection_pc:
                    if not any(priority_movie.lower() in movie["title"].lower() for priority_movie in priority_movies):
                        tab_movies_pc.append(movie)

            # 合并优先电影和普通电影，并限制数量
            tab_movies_pc = priority_movies_pc + tab_movies_pc
            tab_movies_pc = tab_movies_pc[:result_retain_count]
            all_results.extend(tab_movies_pc)
            print(f"标签页 '{tab.get('tab_name', 'Unknown')}' 贡献了 {len(tab_movies_pc)} 个项目")

        # 检查是否有有效的 selected_parent_ids
        if not has_selected_parent_id:
            print("错误：没有标签页包含 selected_parent_ids")
            self.show_error_popup("没有标签页包含 selected_parent_ids。")
            sys.exit(1)

        total_count = len(all_results)
        print(f"轮播项目总数：{total_count}")
        for item in all_results:
            print(f"项目：{item}")

        # 保存轮播数据到 data_pc.js
        try:
            with open("data_pc.js", "w", encoding="utf-8") as f:
                # 写入 JavaScript 代码和轮播数据
                f.write(
                    '// 过渡效果 fade slideLeft slideRight slideTop slideBottom zoom rotate skew none random \n\n'
                    'jQuery(function(){new Nex({delay:10e3,transition:"zoom",style:{type:"circle",filter:"saturate",'
                    'pattern:"",background:"#046ecf",hover:"#055bab",color:"#ffffff"},data:[\n'
                )
                for movie in all_results:
                    f.write(json.dumps(movie, ensure_ascii=False) + ',\n')
                f.write(']});});')
            print("成功保存轮播数据到 data_pc.js")
        except Exception as e:
            print(f"错误：保存 data_pc.js 失败：{e}")
            sys.exit(1)

def main():
    # 主函数，创建 SilentCarouselGenerator 实例并生成轮播
    generator = SilentCarouselGenerator()
    generator.generate_carousel()

if __name__ == "__main__":
    main()