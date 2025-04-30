import sys
import json
import requests
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTabWidget, QMessageBox, QGroupBox, QGridLayout,
    QScrollArea, QTableWidget, QTableWidgetItem, QComboBox, QCheckBox,
    QTextEdit, QListWidget, QListWidgetItem, QInputDialog, QTabBar, QDialog, QFormLayout
)
from PyQt5.QtCore import Qt, QTimer
from datetime import datetime, timedelta


class EmbyConfigGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.EMBY_SERVER = ""
        self.EMBY_API_KEY = ""
        self.all_libraries = []
        self.tab_settings = []
        self.next_tab_index = 2  # 从 2 开始（0: 配置，1: 每日电影）
        self.max_dynamic_tabs = 10
        self.dynamic_tab_count = 0
        self.tab_names = {}
        self.is_moving = False
        self.descriptions = {
            1: (
                "这是一份温暖的陪伴，也是每天的新鲜惊喜。我们为您精心挑选全球电影精品，每一天，都有一部独特的电影等待您的欣赏。",
                "DAILY MOVIE"
            ),
        }
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabBar(CustomTabBar(self))
        self.tab_widget.setMovable(True)
        self.tab_widget.tabBar().tabMoved.connect(self.on_tab_moved)
        
        # 添加配置选项卡
        tab1 = self.create_config_tab()
        self.tab_widget.addTab(tab1, "配置录入")
        
        # 添加每日电影选项卡
        self.add_tab_with_collection_settings(self.tab_widget, "每日电影", 1)
        
        # 添加“+”号选项卡
        self.add_plus_tab()
        
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
        self.setWindowTitle('Emby 配置录入工具')
        self.show()

    def add_plus_tab(self):
        add_tab = QWidget()
        self.tab_widget.addTab(add_tab, "+")

    def add_new_tab(self):
        if self.dynamic_tab_count >= self.max_dynamic_tabs:
            QMessageBox.warning(self, "警告", f"动态选项卡数量已达上限 ({self.max_dynamic_tabs})")
            return
        dialog = NewTabDialog(self)
        if dialog.exec_():
            tab_name = dialog.get_tab_name()
            template = dialog.get_template()
            self.tab_widget.removeTab(self.tab_widget.count() - 1)
            self.add_tab_with_collection_settings(self.tab_widget, tab_name, self.next_tab_index, template)
            self.tab_names[self.next_tab_index] = tab_name
            print(f"添加新选项卡: 索引={self.next_tab_index}, 名称={tab_name}")
            self.add_plus_tab()
            self.tab_widget.setCurrentIndex(self.tab_widget.count() - 2)
            self.next_tab_index += 1
            self.dynamic_tab_count += 1

    def rename_tab(self, index):
        if index < 2:  # 固定选项卡（0: 配置，1: 每日电影）
            return
        tab_index = index + 1
        old_name = self.tab_names.get(tab_index, self.tab_widget.tabText(index))
        new_name, ok = QInputDialog.getText(self, "重命名选项卡", "请输入新的选项卡名称:", text=old_name)
        if ok and new_name:
            self.tab_widget.setTabText(index, new_name)
            self.tab_names[tab_index] = new_name
            print(f"重命名选项卡: 索引={tab_index}, 旧名称={old_name}, 新名称={new_name}")

    def remove_tab(self, index):
        if index < 2:
            return
        tab_index = index + 1
        tab_name = self.tab_widget.tabText(index)
        reply = QMessageBox.question(self, "确认删除", f"确定删除选项卡 '{tab_name}' 吗？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.tab_widget.removeTab(index)
                self.tab_settings.pop(index - 1)
                self.dynamic_tab_count -= 1
                if tab_index in self.tab_names:
                    del self.tab_names[tab_index]
                print(f"删除选项卡: 索引={tab_index}, 名称={tab_name}")
            except Exception as e:
                print(f"Error in remove_tab: {e}")
                QMessageBox.critical(self, "错误", f"删除选项卡失败: {e}")

    def on_tab_moved(self, from_index, to_index):
        if self.is_moving:
            return
        self.is_moving = True
        try:
            if to_index < 2 or to_index == self.tab_widget.count() - 1:
                self.tab_widget.tabBar().moveTab(to_index, from_index)
                return
            if from_index < 2:
                self.tab_widget.tabBar().moveTab(to_index, from_index)
                return
            if 0 <= from_index - 1 < len(self.tab_settings) and 0 <= to_index - 1 < len(self.tab_settings):
                settings_item = self.tab_settings.pop(from_index - 1)
                self.tab_settings.insert(to_index - 1, settings_item)
            new_tab_names = {}
            for i in range(2, self.tab_widget.count() - 1):
                tab_index = i + 1
                tab_text = self.tab_widget.tabText(i)
                new_tab_names[tab_index] = tab_text
            self.tab_names.update(new_tab_names)
            print(f"移动选项卡: 从索引={from_index} 到索引={to_index}, 新tab_names={self.tab_names}")
        except Exception as e:
            print(f"Error in on_tab_moved: {e}")
            QMessageBox.critical(self, "错误", f"移动选项卡失败: {e}")
        finally:
            QTimer.singleShot(100, self.reset_moving)

    def reset_moving(self):
        self.is_moving = False

    def create_config_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout()
        self.serverip_input = QLineEdit()
        serverip_layout = self.create_input_layout("服务器IP:", self.serverip_input, "http://127.0.0.1:8096")
        tab_layout.addLayout(serverip_layout)
        self.apikey_input = QLineEdit()
        apikey_layout = self.create_input_layout("APIKEY:", self.apikey_input)
        tab_layout.addLayout(apikey_layout)
        save_all_button = QPushButton("保存配置")
        save_all_button.clicked.connect(self.save_all_config)
        tab_layout.addWidget(save_all_button)
        load_button = QPushButton("载入配置")
        load_button.clicked.connect(self.load_config)
        tab_layout.addWidget(load_button)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        self.server_id_label = QLabel("")
        server_id_group = self.create_group_box("ServerID", QGridLayout(), self.server_id_label)
        scroll_layout.addWidget(server_id_group)
        self.movie_libraries_table = QTableWidget()
        movie_libraries_group = self.create_library_group_box("电影媒体库", self.movie_libraries_table)
        scroll_layout.addWidget(movie_libraries_group)
        self.tvshow_libraries_table = QTableWidget()
        tvshow_libraries_group = self.create_library_group_box("剧集媒体库", self.tvshow_libraries_table)
        scroll_layout.addWidget(tvshow_libraries_group)
        self.boxset_libraries_table = QTableWidget()
        boxset_libraries_group = self.create_library_group_box("合集媒体库", self.boxset_libraries_table)
        scroll_layout.addWidget(boxset_libraries_group)
        scroll_content.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_content)
        tab_layout.addWidget(scroll_area)
        tab.setLayout(tab_layout)
        return tab

    def create_input_layout(self, label_text, line_edit, placeholder_text=""):
        layout = QHBoxLayout()
        label = QLabel(label_text)
        line_edit.setPlaceholderText(placeholder_text)
        layout.addWidget(label)
        layout.addWidget(line_edit)
        return layout

    def create_group_box(self, title, layout, widget=None):
        group_box = QGroupBox(title)
        if widget:
            layout.addWidget(widget)
        group_box.setLayout(layout)
        return group_box

    def create_library_group_box(self, title, table_widget):
        group_box = QGroupBox(title)
        self.setup_table(table_widget)
        group_box.setLayout(QVBoxLayout())
        group_box.layout().addWidget(table_widget)
        return group_box

    def update_parent_id_checkboxes(self, settings):
        include_item_types_combo = settings["include_item_types_combo"]
        parent_id_list = settings["parent_id_list"]
        tab_name = settings.get("tab_name", "Unknown")
        selected_type = include_item_types_combo.currentText()
        type_map = {"Movie": "movies", "Series": "tvshows", "BoxSet": "boxsets"}
        collection_type = type_map.get(selected_type, "").lower()
        print(f"更新选项卡 '{tab_name}' 的 parent_id_checkboxes，媒体类型: '{selected_type}'")
        if not self.all_libraries:
            print(f"警告: 选项卡 '{tab_name}' 的 all_libraries 为空")
            return
        for i in range(parent_id_list.count()):
            item = parent_id_list.item(i)
            matching_lib = next((lib for lib in self.all_libraries if lib["Name"] == item.text() and lib["ItemId"] == item.data(Qt.UserRole)), None)
            if matching_lib and matching_lib.get("CollectionType", "").lower() == collection_type:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)

    def add_tab_with_collection_settings(self, tab_widget, tab_name, tab_index, template=None):
        tab = QWidget()
        tab_layout = QVBoxLayout()
        if tab_index > 1:
            header_layout = QHBoxLayout()
            rename_button = QPushButton("重命名")
            rename_button.setStyleSheet("font-size: 12px; padding: 2px;")
            rename_button.clicked.connect(lambda: self.rename_tab(tab_widget.indexOf(tab)))
            delete_button = QPushButton("删除")
            delete_button.setStyleSheet("font-size: 12px; padding: 2px; background-color: #e74c3c; color: white;")
            delete_button.clicked.connect(lambda: self.remove_tab(tab_widget.indexOf(tab)))
            header_layout.addWidget(rename_button)
            header_layout.addWidget(delete_button)
            header_layout.addStretch()
            tab_layout.addLayout(header_layout)
        enabled_checkbox = QCheckBox("启用此配置")
        enabled_checkbox.setChecked(True)
        tab_layout.addWidget(enabled_checkbox)
        collection_settings_group = self.create_group_box("数据抽取配置", QGridLayout())
        parent_id_label = QLabel("抽取媒体库（可多选）:")
        parent_id_list = QListWidget()
        collection_settings_group.layout().addWidget(parent_id_label, 0, 0)
        collection_settings_group.layout().addWidget(parent_id_list, 0, 1)
        custom_parent_id_label = QLabel("添加自定义抽取源:")
        custom_parent_id_input = QLineEdit()
        custom_parent_id_input.setPlaceholderText("输入名称或 ItemId")
        add_custom_parent_id_button = QPushButton("添加")
        custom_parent_id_layout = QHBoxLayout()
        custom_parent_id_layout.addWidget(custom_parent_id_input)
        custom_parent_id_layout.addWidget(add_custom_parent_id_button)
        collection_settings_group.layout().addWidget(custom_parent_id_label, 1, 0)
        collection_settings_group.layout().addLayout(custom_parent_id_layout, 1, 1)
        clear_all_button = QPushButton("清空勾选")
        clear_all_button.clicked.connect(lambda: self.clear_all_selections(parent_id_list))
        button_layout = QHBoxLayout()
        button_layout.addWidget(clear_all_button)
        collection_settings_group.layout().addLayout(button_layout, 2, 0, 1, 2)
        recursive_label = QLabel("含子目录:")
        recursive_checkbox = QCheckBox()
        collection_settings_group.layout().addWidget(recursive_label, 3, 0)
        collection_settings_group.layout().addWidget(recursive_checkbox, 3, 1)
        sortby_label = QLabel("筛选依据:")
        sortby_combo = QComboBox()
        self.populate_combo(sortby_combo, [
            ("Random", "随机"), ("PremiereDate", "首映日期"), ("ProductionYear", "制作年份"),
            ("SortName", "名称"), ("DateCreated", "创建日期"), ("Album", "专辑"),
            ("AlbumArtist", "专辑艺术家"), ("Artist", "艺术家"), ("Budget", "预算"),
            ("CommunityRating", "社区评级"), ("CriticRating", "评论家评级"), ("DatePlayed", "播放日期"),
            ("PlayCount", "播放次数"), ("Revenue", "收入"), ("Runtime", "片长")
        ])
        collection_settings_group.layout().addWidget(sortby_label, 4, 0)
        collection_settings_group.layout().addWidget(sortby_combo, 4, 1)
        include_item_types_label = QLabel("媒体类型:")
        include_item_types_combo = QComboBox()
        self.populate_combo(include_item_types_combo, [("Movie", "Movie"), ("Series", "Series"), ("BoxSet", "BoxSet")])
        collection_settings_group.layout().addWidget(include_item_types_label, 5, 0)
        collection_settings_group.layout().addWidget(include_item_types_combo, 5, 1)
        sort_order_label = QLabel("排序方式:")
        sort_order_combo = QComboBox()
        self.populate_combo(sort_order_combo, [("Ascending", "正序"), ("Descending", "倒序")])
        collection_settings_group.layout().addWidget(sort_order_label, 6, 0)
        collection_settings_group.layout().addWidget(sort_order_combo, 6, 1)
        retain_count_label = QLabel("每个库搜索数:")
        retain_count_combo = QComboBox()
        for i in range(1, 11):
            retain_count_combo.addItem(str(i))
        collection_settings_group.layout().addWidget(retain_count_label, 7, 0)
        collection_settings_group.layout().addWidget(retain_count_combo, 7, 1)
        result_retain_count_label = QLabel("结果保留数:")
        result_retain_count_input = QLineEdit()
        result_retain_count_input.setText("1")
        collection_settings_group.layout().addWidget(result_retain_count_label, 8, 0)
        collection_settings_group.layout().addWidget(result_retain_count_input, 8, 1)
        priority_movies_label = QLabel("优先展示:")
        priority_movies_input = QLineEdit()
        priority_movies_input.setPlaceholderText("指定抽取特定影片，中文逗号分割")
        collection_settings_group.layout().addWidget(priority_movies_label, 9, 0)
        collection_settings_group.layout().addWidget(priority_movies_input, 9, 1)
        min_premiere_date_label = QLabel("距今上映:")
        min_premiere_date_input = QLineEdit()
        min_premiere_date_input.setPlaceholderText("输入天数")
        collection_settings_group.layout().addWidget(min_premiere_date_label, 10, 0)
        collection_settings_group.layout().addWidget(min_premiere_date_input, 10, 1)
        tab_layout.addWidget(collection_settings_group)
        generate_button = QPushButton("生成轮播")
        generate_button.clicked.connect(self.generate_carousel)
        tab_layout.addWidget(generate_button)
        carousel_count_label = QLabel("总轮播图数量: 0")
        tab_layout.addWidget(carousel_count_label)
        items_info_textedit = QTextEdit()
        items_info_textedit.setReadOnly(True)
        items_info_textedit.setLineWrapMode(QTextEdit.WidgetWidth)
        tab_layout.addWidget(items_info_textedit)
        tab.setLayout(tab_layout)
        tab_widget.addTab(tab, tab_name)
        settings = {
            "enabled_checkbox": enabled_checkbox,
            "parent_id_list": parent_id_list,
            "recursive_checkbox": recursive_checkbox,
            "sortby_combo": sortby_combo,
            "sort_order_combo": sort_order_combo,
            "include_item_types_combo": include_item_types_combo,
            "retain_count_combo": retain_count_combo,
            "priority_movies_input": priority_movies_input,
            "min_premiere_date_input": min_premiere_date_input,
            "carousel_count_label": carousel_count_label,
            "items_info_textedit": items_info_textedit,
            "result_retain_count_input": result_retain_count_input,
            "custom_parent_id_input": custom_parent_id_input,
            "tab_name": tab_name
        }
        self.tab_settings.append(settings)
        add_custom_parent_id_button.clicked.connect(lambda: self.add_custom_parent_id(settings))
        include_item_types_combo.currentIndexChanged.connect(lambda: self.update_parent_id_checkboxes(settings))
        if self.EMBY_SERVER and self.EMBY_API_KEY:
            self.get_all_libraries(settings)
        self.customize_tab(tab_index, recursive_checkbox, include_item_types_combo,
                         sort_order_combo, sortby_combo, min_premiere_date_input,
                         parent_id_list, template)
        self.update_parent_id_checkboxes(settings)

    def populate_combo(self, combo, options):
        for key, value in options:
            combo.addItem(value, key)

    def customize_tab(self, tab_index, recursive_checkbox, include_item_types_combo,
                     sort_order_combo, sortby_combo, min_premiere_date_input,
                     parent_id_list, template=None):
        if tab_index in self.descriptions:
            description, tips = self.descriptions[tab_index]
            self.description = description
            self.tips = tips
        if tab_index == 1:  # 每日电影
            recursive_checkbox.setChecked(True)
            sortby_combo.setCurrentIndex(sortby_combo.findData("Random"))
            include_item_types_combo.setCurrentText("Movie")
        else:  # 动态选项卡
            if template == "new_releases":
                recursive_checkbox.setChecked(True)
                include_item_types_combo.setCurrentText("Movie")
                sort_order_combo.setCurrentText("倒序")
                sortby_combo.setCurrentIndex(sortby_combo.findData("PremiereDate"))
                min_premiere_date_input.setText("45")
            elif template == "recent_series":
                recursive_checkbox.setChecked(False)
                include_item_types_combo.setCurrentText("Series")
                sort_order_combo.setCurrentText("倒序")
                sortby_combo.setCurrentIndex(sortby_combo.findData("PremiereDate"))
            elif template == "film_collection":
                recursive_checkbox.setChecked(False)
                include_item_types_combo.setCurrentText("BoxSet")
                sortby_combo.setCurrentIndex(sortby_combo.findData("Random"))
            elif template == "movie":
                recursive_checkbox.setChecked(True)
                sortby_combo.setCurrentIndex(sortby_combo.findData("Random"))
                include_item_types_combo.setCurrentText("Movie")
            elif template == "series":
                recursive_checkbox.setChecked(False)
                include_item_types_combo.setCurrentText("Series")
                sort_order_combo.setCurrentText("倒序")
                sortby_combo.setCurrentIndex(sortby_combo.findData("PremiereDate"))
            elif template == "boxset":
                recursive_checkbox.setChecked(False)
                include_item_types_combo.setCurrentText("BoxSet")
                sortby_combo.setCurrentIndex(sortby_combo.findData("Random"))
            else:  # 默认
                recursive_checkbox.setChecked(True)
                sortby_combo.setCurrentIndex(sortby_combo.findData("Random"))
                include_item_types_combo.setCurrentText("Movie")

    def setup_table(self, table):
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["媒体库名称", "媒体库 ITEMID"])
        table.setStyleSheet("""
            QTableWidget {
                border-radius: 10px;
                border: 1px solid #ccc;
                background-color: #f9f9f9;
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 1px;
                font-size: 12px;
                border-bottom: 1px solid #e0e0e0;
            }
            QHeaderView::section {
                background-color: #e0e0e0;
                padding: 1px;
                border: 1px solid #ccc;
                font-size: 12px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        table.setEditTriggers(QTableWidget.NoEditTriggers)

    def save_all_config(self):
        serverip = self.serverip_input.text() or "http://127.0.0.1:8096"
        apikey = self.apikey_input.text()
        config = {
            "EMBY_SERVER": serverip.rstrip("/") + "/",
            "EMBY_API_KEY": apikey,
            "tabs": []
        }
        for index, settings in enumerate(self.tab_settings):
            tab_index = index + 1
            tab_name = self.tab_names.get(tab_index, self.tab_widget.tabText(index + 1))
            tab_config = {
                "enabled": settings["enabled_checkbox"].isChecked(),
                "include_item_type": settings["include_item_types_combo"].currentText(),
                "sort_by": settings["sortby_combo"].currentData(),
                "sort_order": settings["sort_order_combo"].currentData(),
                "retain_count": settings["retain_count_combo"].currentText(),
                "result_retain_count": settings["result_retain_count_input"].text(),
                "priority_movies": settings["priority_movies_input"].text(),
                "min_premiere_days": settings["min_premiere_date_input"].text(),
                "selected_parent_ids": [],
                "tab_name": tab_name
            }
            for i in range(settings["parent_id_list"].count()):
                item = settings["parent_id_list"].item(i)
                if item.checkState() == Qt.Checked:
                    tab_config["selected_parent_ids"].append(item.data(Qt.UserRole))
            config["tabs"].append(tab_config)
            print(f"保存选项卡: 索引={tab_index}, 名称={tab_name}")
        try:
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "提示", "全部配置保存成功")
            if serverip and apikey:
                self.EMBY_SERVER = serverip.rstrip("/") + "/"
                self.EMBY_API_KEY = apikey
                self.show_server_and_library_info()
                self.get_all_libraries()
                for settings in self.tab_settings:
                    self.update_parent_id_checkboxes(settings)
                QMessageBox.information(self, "提示", "已自动加载服务器和媒体库信息")
        except Exception as e:
            print(f"Error in save_all_config: {e}")
            QMessageBox.critical(self, "错误", f"保存配置失败: {e}")

    def load_config(self):
        try:
            with open("config.json", "r", encoding="utf-8-sig") as f:
                config = json.load(f)
                self.serverip_input.setText(config["EMBY_SERVER"].rstrip("/"))
                self.apikey_input.setText(config["EMBY_API_KEY"])
                self.EMBY_SERVER = config["EMBY_SERVER"]
                self.EMBY_API_KEY = config["EMBY_API_KEY"]
                self.get_all_libraries()
                if not self.all_libraries:
                    QMessageBox.warning(self, "警告", "无法加载媒体库信息，请检查 SERVERIP 和 APIKEY")
                    return
                while len(self.tab_settings) > 1:  # 保留每日电影
                    self.tab_widget.removeTab(2)
                    self.tab_settings.pop()
                    self.dynamic_tab_count -= 1
                self.next_tab_index = 2
                self.dynamic_tab_count = 0
                self.tab_names = {}
                for settings in self.tab_settings:
                    settings["parent_id_list"].clear()
                    for lib in self.all_libraries:
                        item = QListWidgetItem(lib["Name"])
                        item.setData(Qt.UserRole, lib["ItemId"])
                        item.setCheckState(Qt.Unchecked)
                        settings["parent_id_list"].addItem(item)
                if "tabs" in config:
                    for i, (tab_config, settings) in enumerate(zip(config["tabs"][:1], self.tab_settings)):
                        settings["enabled_checkbox"].setChecked(tab_config.get("enabled", True))
                        include_item_type = tab_config.get("include_item_type", "Movie")
                        if include_item_type not in ["Movie", "Series", "BoxSet"]:
                            include_item_type = "Movie"
                        settings["include_item_types_combo"].setCurrentText(include_item_type)
                        settings["sortby_combo"].setCurrentIndex(settings["sortby_combo"].findData(tab_config.get("sort_by")))
                        settings["sort_order_combo"].setCurrentIndex(settings["sort_order_combo"].findData(tab_config.get("sort_order")))
                        settings["retain_count_combo"].setCurrentText(tab_config.get("retain_count", "2"))
                        settings["result_retain_count_input"].setText(tab_config.get("result_retain_count", "2"))
                        settings["priority_movies_input"].setText(tab_config.get("priority_movies", ""))
                        settings["min_premiere_date_input"].setText(tab_config.get("min_premiere_days", ""))
                        selected_ids = tab_config.get("selected_parent_ids", [])
                        for j in range(settings["parent_id_list"].count()):
                            item = settings["parent_id_list"].item(j)
                            if item.data(Qt.UserRole) in selected_ids:
                                item.setCheckState(Qt.Checked)
                        self.update_parent_id_checkboxes(settings)
                    for tab_config in config["tabs"][1:]:
                        if self.dynamic_tab_count >= self.max_dynamic_tabs:
                            break
                        tab_name = tab_config.get("tab_name", f"自定义{self.dynamic_tab_count + 1}")
                        self.tab_widget.removeTab(self.tab_widget.count() - 1)
                        self.add_tab_with_collection_settings(self.tab_widget, tab_name, self.next_tab_index)
                        self.tab_names[self.next_tab_index] = tab_name
                        self.add_plus_tab()
                        settings = self.tab_settings[-1]
                        settings["enabled_checkbox"].setChecked(tab_config.get("enabled", True))
                        include_item_type = tab_config.get("include_item_type", "Movie")
                        if include_item_type not in ["Movie", "Series", "BoxSet"]:
                            include_item_type = "Movie"
                        settings["include_item_types_combo"].setCurrentText(include_item_type)
                        settings["sortby_combo"].setCurrentIndex(settings["sortby_combo"].findData(tab_config.get("sort_by")))
                        settings["sort_order_combo"].setCurrentIndex(settings["sort_order_combo"].findData(tab_config.get("sort_order")))
                        settings["retain_count_combo"].setCurrentText(tab_config.get("retain_count", "2"))
                        settings["result_retain_count_input"].setText(tab_config.get("result_retain_count", "2"))
                        settings["priority_movies_input"].setText(tab_config.get("priority_movies", ""))
                        settings["min_premiere_date_input"].setText(tab_config.get("min_premiere_days", ""))
                        selected_ids = tab_config.get("selected_parent_ids", [])
                        for j in range(settings["parent_id_list"].count()):
                            item = settings["parent_id_list"].item(j)
                            if item.data(Qt.UserRole) in selected_ids:
                                item.setCheckState(Qt.Checked)
                        self.update_parent_id_checkboxes(settings)
                        print(f"加载动态选项卡: 索引={self.next_tab_index}, 名称={tab_name}")
                        self.next_tab_index += 1
                        self.dynamic_tab_count += 1
                else:
                    for settings in self.tab_settings:
                        self.update_parent_id_checkboxes(settings)
            QMessageBox.information(self, "提示", "配置文件载入成功")
            self.show_server_and_library_info()
        except FileNotFoundError:
            QMessageBox.warning(self, "警告", "未找到配置文件 config.json")
        except Exception as e:
            print(f"Error in load_config: {e}")
            QMessageBox.critical(self, "错误", f"载入配置文件失败: {e}")

    def show_server_and_library_info(self):
        serverip = self.serverip_input.text()
        apikey = self.apikey_input.text()
        if not serverip or not apikey:
            QMessageBox.warning(self, "警告", "请输入有效的 SERVERIP 和 APIKEY")
            return
        try:
            server_info_url = f"{serverip.rstrip('/')}/System/Info?api_key={apikey}"
            server_info_response = requests.get(server_info_url)
            server_info_response.raise_for_status()
            server_info = server_info_response.json()
            self.server_id_label.setText(server_info.get("Id", "未获取到 ServerID"))
            libraries_url = f"{serverip.rstrip('/')}/Library/VirtualFolders?api_key={apikey}"
            libraries_response = requests.get(libraries_url)
            libraries_response.raise_for_status()
            libraries = libraries_response.json()
            movie_libraries = [lib for lib in libraries if lib.get("CollectionType", "").lower() == "movies"]
            tvshow_libraries = [lib for lib in libraries if lib.get("CollectionType", "").lower() == "tvshows"]
            boxset_libraries = [lib for lib in libraries if lib.get("CollectionType", "").lower() == "boxsets"]
            self.populate_table(self.movie_libraries_table, movie_libraries, serverip, apikey)
            self.populate_table(self.tvshow_libraries_table, tvshow_libraries, serverip, apikey)
            self.populate_table(self.boxset_libraries_table, boxset_libraries, serverip, apikey)
        except requests.RequestException as e:
            print(f"Error in show_server_and_library_info: {e}")
            QMessageBox.critical(self, "错误", f"请求服务器信息失败: {e}")
        except Exception as e:
            print(f"Error in show_server_and_library_info: {e}")
            QMessageBox.critical(self, "错误", f"处理服务器信息失败: {e}")

    def populate_table(self, table, libraries, serverip, apikey):
        table.setRowCount(len(libraries))
        for row, lib in enumerate(libraries):
            table.setRowHeight(row, 20)
            name_item = QTableWidgetItem(lib['Name'])
            name_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 0, name_item)
            item_id_item = QTableWidgetItem(str(lib['ItemId']))
            item_id_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 1, item_id_item)

    def get_all_libraries(self, current_settings=None):
        if not self.EMBY_SERVER or not self.EMBY_API_KEY:
            return
        libraries_url = f"{self.EMBY_SERVER.rstrip('/')}/Library/VirtualFolders?api_key={self.EMBY_API_KEY}"
        try:
            libraries_response = requests.get(libraries_url)
            libraries_response.raise_for_status()
            self.all_libraries = libraries_response.json()
            if current_settings:
                parent_id_list = current_settings["parent_id_list"]
                parent_id_list.clear()
                for lib in self.all_libraries:
                    item = QListWidgetItem(lib["Name"])
                    item.setData(Qt.UserRole, lib["ItemId"])
                    item.setCheckState(Qt.Unchecked)
                    parent_id_list.addItem(item)
            else:
                for settings in self.tab_settings:
                    parent_id_list = settings["parent_id_list"]
                    parent_id_list.clear()
                    for lib in self.all_libraries:
                        item = QListWidgetItem(lib["Name"])
                        item.setData(Qt.UserRole, lib["ItemId"])
                        item.setCheckState(Qt.Unchecked)
                        parent_id_list.addItem(item)
        except requests.RequestException as e:
            print(f"Failed to fetch libraries: {e}")
            self.all_libraries = []
            QMessageBox.critical(self, "错误", f"请求所有媒体库信息失败: {e}")
        except Exception as e:
            print(f"Error processing libraries: {e}")
            self.all_libraries = []
            QMessageBox.critical(self, "错误", f"处理所有媒体库信息失败: {e}")

    def clear_all_selections(self, parent_id_list):
        for i in range(parent_id_list.count()):
            parent_id_list.item(i).setCheckState(Qt.Unchecked)

    def add_custom_parent_id(self, settings):
        parent_id_list = settings["parent_id_list"]
        custom_input = settings["custom_parent_id_input"].text().strip()
        if not custom_input:
            QMessageBox.warning(self, "警告", "请输入名称或 ItemId")
            return
        if not self.EMBY_SERVER or not self.EMBY_API_KEY:
            QMessageBox.warning(self, "警告", "请先载入有效的 SERVERIP 和 APIKEY 配置")
            return
        if custom_input.isdigit():
            try:
                url = f"{self.EMBY_SERVER.rstrip('/')}/emby/Items/{custom_input}?api_key={self.EMBY_API_KEY}"
                response = requests.get(url)
                response.raise_for_status()
                item = response.json()
                name = item.get("Name", "未知名称")
                item_id = item.get("Id", custom_input)
                for i in range(parent_id_list.count()):
                    if parent_id_list.item(i).data(Qt.UserRole) == item_id:
                        QMessageBox.warning(self, "警告", f"ItemId {item_id} 已存在")
                        return
                list_item = QListWidgetItem(name)
                list_item.setData(Qt.UserRole, item_id)
                list_item.setCheckState(Qt.Checked)
                parent_id_list.addItem(list_item)
                settings["custom_parent_id_input"].clear()
                QMessageBox.information(self, "提示", f"已添加: {name} (ItemId: {item_id})")
            except requests.RequestException as e:
                print(f"Error in add_custom_parent_id: {e}")
                QMessageBox.critical(self, "错误", f"无法获取 ItemId {custom_input} 的信息: {e}")
            except Exception as e:
                print(f"Error in add_custom_parent_id: {e}")
                QMessageBox.critical(self, "错误", f"处理 ItemId {custom_input} 失败: {e}")
        else:
            try:
                url = f"{self.EMBY_SERVER.rstrip('/')}/emby/Items?SearchTerm={custom_input}&Recursive=true&api_key={self.EMBY_API_KEY}"
                response = requests.get(url)
                response.raise_for_status()
                items = response.json().get("Items", [])
                if not items:
                    QMessageBox.warning(self, "警告", f"未找到名称为 '{custom_input}' 的项")
                    return
                item = items[0]
                name = item.get("Name", "未知名称")
                item_id = item.get("Id")
                for i in range(parent_id_list.count()):
                    if parent_id_list.item(i).data(Qt.UserRole) == item_id:
                        QMessageBox.warning(self, "警告", f"ItemId {item_id} 已存在")
                        return
                list_item = QListWidgetItem(name)
                list_item.setData(Qt.UserRole, item_id)
                list_item.setCheckState(Qt.Checked)
                parent_id_list.addItem(list_item)
                settings["custom_parent_id_input"].clear()
                QMessageBox.information(self, "提示", f"已添加: {name} (ItemId: {item_id})")
            except requests.RequestException as e:
                print(f"Error in add_custom_parent_id: {e}")
                QMessageBox.critical(self, "错误", f"搜索名称 '{custom_input}' 失败: {e}")
            except Exception as e:
                print(f"Error in add_custom_parent_id: {e}")
                QMessageBox.critical(self, "错误", f"处理名称 '{custom_input}' 失败: {e}")

    def get_movies(self, params, limit, retain_count, default_overview, tips, check_run_time_ticks=True):
        try:
            response = requests.get(f"{self.EMBY_SERVER}/emby/Items", params=params)
            response.raise_for_status()
            movies_pc = []
            run_time_ticks_set = set()
            previous_movie_title = None
            previous_run_time_ticks = None
            for item in response.json().get("Items", []):
                run_time_ticks = item.get("RunTimeTicks") if check_run_time_ticks else None
                if check_run_time_ticks and run_time_ticks in run_time_ticks_set:
                    continue
                if check_run_time_ticks and run_time_ticks == previous_run_time_ticks:
                    continue
                title = item.get("Name", "")
                if title == previous_movie_title:
                    continue
                run_time_ticks_set.add(run_time_ticks)
                image_url1 = f"{self.EMBY_SERVER}/emby/Items/{item['Id']}/Images/Backdrop"
                image_url2 = f"{self.EMBY_SERVER}/emby/Items/{item['Id']}/Images/Primary"
                image_url3 = f"{self.EMBY_SERVER}/emby/Items/{item['Id']}/Images/Logo"
                movie_pc = {
                    "display": "image",
                    "link": image_url1,
                    "title": item["Name"],
                    "description": item.get("Overview", default_overview).replace('"', ''),
                    "thumb": image_url2,
                    "url": "#",
                    "alt": item["Id"],
                    "tips": tips,
                    "logo": image_url3,
                }
                movies_pc.append(movie_pc)
                previous_movie_title = movie_pc["title"]
                previous_run_time_ticks = run_time_ticks
                if len(movies_pc) == limit:
                    break
            return movies_pc[:retain_count]
        except requests.RequestException as e:
            print(f"Error in get_movies: {e}")
            raise
        except Exception as e:
            print(f"Error in get_movies: {e}")
            raise

    def generate_carousel(self):
        if not self.EMBY_SERVER or not self.EMBY_API_KEY:
            QMessageBox.warning(self, "警告", "请先载入有效的 SERVERIP 和 APIKEY 配置")
            return
        all_results = []
        has_selected_parent_id = False
        for index, settings in enumerate(self.tab_settings):
            if not settings["enabled_checkbox"].isChecked():
                continue
            parent_id_list = settings["parent_id_list"]
            recursive_checkbox = settings["recursive_checkbox"]
            sortby_combo = settings["sortby_combo"]
            sort_order_combo = settings["sort_order_combo"]
            include_item_types_combo = settings["include_item_types_combo"]
            retain_count_combo = settings["retain_count_combo"]
            priority_movies_input = settings["priority_movies_input"]
            min_premiere_date_input = settings["min_premiere_date_input"]
            result_retain_count_input = settings["result_retain_count_input"]
            try:
                result_retain_count = int(result_retain_count_input.text())
            except ValueError:
                QMessageBox.warning(self, "警告", "结果保留数必须为整数")
                continue
            retain_count = int(retain_count_combo.currentText())
            limit = retain_count * 2
            selected_parent_ids = [item.data(Qt.UserRole) for item in parent_id_list.findItems("", Qt.MatchContains) if item.checkState() == Qt.Checked]
            if selected_parent_ids:
                has_selected_parent_id = True
            if not selected_parent_ids:
                continue
            sortby = sortby_combo.currentData()
            sort_order = sort_order_combo.currentData()
            recursive = recursive_checkbox.isChecked()
            include_item_types = include_item_types_combo.currentText()
            priority_movies = [movie.strip() for movie in priority_movies_input.text().split('，') if movie.strip()]
            min_premiere_days = min_premiere_date_input.text()
            min_premiere_date = None
            if min_premiere_days:
                try:
                    min_premiere_days = int(min_premiere_days)
                    min_premiere_date = (datetime.now() - timedelta(days=min_premiere_days)).isoformat()
                except ValueError:
                    QMessageBox.warning(self, "警告", "MinPremiereDate 输入的天数必须是整数")
                    continue
            description, tips = self.descriptions.get(index + 1, (
                "这是您探索电影系列世界的优选之地。",
                "CUSTOM COLLECTION"
            ))
            tab_movies_pc = []
            priority_movies_pc = []
            for parent_id in selected_parent_ids:
                for priority_movie in priority_movies:
                    params = {
                        "Limit": limit,
                        "ParentId": parent_id,
                        "Recursive": recursive,
                        "Fields": "Overview",
                        "SortBy": sortby,
                        "SortOrder": sort_order,
                        "IncludeItemTypes": include_item_types,
                        "api_key": self.EMBY_API_KEY,
                        "NameStartsWith": priority_movie
                    }
                    if min_premiere_date:
                        params["MinPremiereDate"] = min_premiere_date
                    try:
                        collection_pc = self.get_movies(params, limit, retain_count, description, tips, check_run_time_ticks=False)
                        for movie in collection_pc:
                            if priority_movie.lower() in movie["title"].lower():
                                priority_movies_pc.append(movie)
                    except Exception as e:
                        print(f"Error in generate_carousel (priority): {e}")
                        QMessageBox.critical(self, "错误", f"无法获取信息: {e}")
                params = {
                    "Limit": limit,
                    "ParentId": parent_id,
                    "Recursive": recursive,
                    "Fields": "Overview",
                    "SortBy": sortby,
                    "SortOrder": sort_order,
                    "IncludeItemTypes": include_item_types,
                    "api_key": self.EMBY_API_KEY
                }
                if min_premiere_date:
                    params["MinPremiereDate"] = min_premiere_date
                try:
                    collection_pc = self.get_movies(params, limit, retain_count, description, tips, check_run_time_ticks=False)
                    for movie in collection_pc:
                        if not any(priority_movie.lower() in movie["title"].lower() for priority_movie in priority_movies):
                            tab_movies_pc.append(movie)
                except Exception as e:
                    print(f"Error in generate_carousel: {e}")
                    QMessageBox.critical(self, "错误", f"无法获取信息: {e}")
            tab_movies_pc = priority_movies_pc + tab_movies_pc
            tab_movies_pc = tab_movies_pc[:result_retain_count]
            all_results.extend(tab_movies_pc)
        if not has_selected_parent_id:
            QMessageBox.warning(self, "警告", "请至少选择一个 ParentId")
            return
        total_count = len(all_results)
        for settings in self.tab_settings:
            settings["carousel_count_label"].setText(f"总轮播图数量: {total_count}")
            settings["items_info_textedit"].setPlainText("\n".join([str(item) for item in all_results]))
        try:
            with open("data_pc.js", "w", encoding='utf-8') as f:
                f.write('// 过渡效果 fade slideLeft slideRight slideTop slideBottom zoom rotate skew none random \n\njQuery(function(){new Nex({delay:10e3,transition:"zoom",style:{type:"circle",filter:"saturate",pattern:"",background:"#046ecf",hover:"#055bab",color:"#ffffff"},data:[\n')
                for movie in all_results:
                    f.write(json.dumps(movie, ensure_ascii=False) + ',\n')
                f.write(']});});')
            QMessageBox.information(self, "提示", "轮播数据已生成并保存到 data_pc.js")
        except Exception as e:
            print(f"Error in generate_carousel (save): {e}")
            QMessageBox.critical(self, "错误", f"保存 data_pc.js 失败: {e}")


class CustomTabBar(QTabBar):
    def __init__(self, parent):
        super().__init__()
        self.parent_widget = parent

    def mouseDoubleClickEvent(self, event):
        index = self.tabAt(event.pos())
        if index >= 0 and index != self.count() - 1:
            self.parent_widget.rename_tab(index)

    def mousePressEvent(self, event):
        index = self.tabAt(event.pos())
        if index == self.count() - 1:
            self.parent_widget.add_new_tab()
        super().mousePressEvent(event)


class NewTabDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("创建新选项卡")
        layout = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setText(f"自定义{parent.dynamic_tab_count + 1}")
        layout.addRow("选项卡名称:", self.name_input)
        self.template_combo = QComboBox()
        self.template_combo.addItems(["默认", "近期上映", "近期剧集", "随机合集", "电影", "剧集", "合集"])
        layout.addRow("模板:", self.template_combo)
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addRow(button_layout)
        self.setLayout(layout)

    def get_tab_name(self):
        return self.name_input.text().strip()

    def get_template(self):
        template_map = {
            "默认": None,
            "近期上映": "new_releases",
            "近期剧集": "recent_series",
            "随机合集": "film_collection",
            "电影": "movie",
            "剧集": "series",
            "合集": "boxset"
        }
        return template_map[self.template_combo.currentText()]


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = EmbyConfigGUI()
    sys.exit(app.exec_())