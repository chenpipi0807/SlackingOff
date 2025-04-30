import sys
import json
import requests
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QAction, QWidgetAction, 
                         QLabel, QDialog, QVBoxLayout, QLineEdit, QPushButton, 
                         QHBoxLayout, QCompleter, QTableWidget, QTableWidgetItem,
                         QHeaderView, QFrame, QMessageBox, QWidget, QMainWindow)
from PyQt5.QtCore import Qt, QTimer, QSize, QStringListModel, QPoint, QEvent, QPropertyAnimation, QRect
from PyQt5.QtGui import (QIcon, QFont, QPixmap, QPainter, QColor, QBrush, QPen,
                    QLinearGradient, QRadialGradient, QFontMetrics, QCursor, QMouseEvent)

# 定义常量和样式
DEFAULT_REFRESH_RATE = 3  # 默认刷新频率（秒）

STYLE_SHEET = """
    QDialog, QMenu {
        background-color: #F5F5F7;
        border-radius: 8px;
    }
    QLabel {
        color: #333333;
        font-family: "Microsoft YaHei", "微软雅黑";
    }
    QLineEdit {
        padding: 6px;
        border: 1px solid #CCCCCC;
        border-radius: 4px;
        background-color: white;
    }
    QPushButton {
        background-color: #1890FF;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 6px 12px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #40A9FF;
    }
    QPushButton:pressed {
        background-color: #096DD9;
    }
    QTableWidget {
        border: 1px solid #EAEAEA;
        border-radius: 4px;
        background-color: white;
    }
    QTableWidget::item:selected {
        background-color: #E6F7FF;
        color: #1890FF;
    }
    QFrame.line {
        background-color: #EAEAEA;
    }
    
    /* 悬浮窗口样式 */
    #FloatingWindow {
        background-color: rgba(40, 40, 45, 0.85);
        border: 1px solid rgba(80, 80, 85, 0.5);
        border-radius: 6px;
    }
    #FloatingWindow QLabel {
        color: white;
        font-family: "Microsoft YaHei", "微软雅黑";
    }
"""

class FloatingWindow(QWidget):
    """可拖动的悬浮股票指数窗口"""
    def __init__(self, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("FloatingWindow")
        
        # 设置固定尺寸 - 增加尺寸
        self.setFixedSize(160, 90)
        
        # 初始化UI
        self._init_ui()
        
        # 拖动相关变量
        self.dragging = False
        self.drag_position = QPoint()
        
        # 延迟展示/隐藏的定时器
        self.fade_timer = None
        self.opacity = 1.0
        
        # 显示窗口
        self.show()
        
        # 初始化鼠标进入离开检测
        self.setMouseTracking(True)
        self.installEventFilter(self)
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        
        # 股票名称和代码
        header_layout = QHBoxLayout()
        
        self.name_label = QLabel()
        self.name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.name_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        
        self.code_label = QLabel()
        self.code_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.code_label.setFont(QFont("Microsoft YaHei", 8))
        self.code_label.setStyleSheet("color: rgba(255,255,255,0.7);")
        
        header_layout.addWidget(self.name_label, 7)
        header_layout.addWidget(self.code_label, 3)
        
        # 股票价格
        self.price_label = QLabel()
        self.price_label.setAlignment(Qt.AlignCenter)
        self.price_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        
        # 涨跌幅
        self.change_label = QLabel()
        self.change_label.setAlignment(Qt.AlignCenter)
        self.change_label.setFont(QFont("Microsoft YaHei", 10))
        
        layout.addLayout(header_layout)
        layout.addWidget(self.price_label)
        layout.addWidget(self.change_label)
    
    def update_stock_info(self, code, name, price, price_change, change_percent):
        """更新股票信息"""
        # 分开显示名称和代码
        self.name_label.setText(f"{name}")
        self.code_label.setText(f"{code}")
        
        # 显示当前价格
        self.price_label.setText(f"{price}")
        
        # 设置涨跌颜色
        color = "#F5222D" if price_change.startswith("+") else "#52C41A"
        self.change_label.setText(f"<span style='color:{color};'>{price_change} ({change_percent})</span>")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            # 右键点击时创建快捷菜单
            menu = QMenu(self)
            close_action = menu.addAction("关闭悬浮窗口")
            menu.popup(QCursor.pos())
            close_action.triggered.connect(self.hide)
    
    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            # 保存位置
            settings = QApplication.instance().property("settings") or {}
            settings["floating_pos"] = {"x": self.x(), "y": self.y()}
            QApplication.instance().setProperty("settings", settings)
    
    def eventFilter(self, obj, event):
        # 监测鼠标进入和离开窗口
        if obj == self:
            if event.type() == QEvent.Enter:
                # 鼠标进入
                if self.fade_timer:
                    self.fade_timer.stop()
                self.setWindowOpacity(1.0)
            elif event.type() == QEvent.Leave:
                # 鼠标离开
                # 2秒后半透明
                QTimer.singleShot(2000, lambda: self.setWindowOpacity(0.7))
        return super().eventFilter(obj, event)


class StockTrayApp:
    def __init__(self):
        # 创建应用
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)  # 关闭窗口时不退出应用
        self.app.setStyleSheet(STYLE_SHEET)  # 应用全局样式
        
        # 存储设置
        self.app.setProperty("settings", {})
        
        # 存储股票代码和当前价格
        self.stock_code = "603019"  # 默认股票代码 - 中科曙光
        self.stock_name = "中科曙光"
        self.current_price = "0.00"
        self.price_change = "+0.00"
        self.change_percent = "+0.00%"
        self.market_status = "休市"  # 市场状态
        self.update_time = "--:--"   # 更新时间
        
        # 创建悬浮窗口
        self.floating_window = FloatingWindow()
        self.floating_window.setWindowOpacity(0.9)  # 初始半透明
        
        # 设置初始位置
        desktop = QApplication.desktop()
        screen_rect = desktop.availableGeometry()
        window_rect = self.floating_window.frameGeometry()
        window_rect.moveCenter(screen_rect.center())
        # 将窗口移动到右下角
        window_rect.moveRight(screen_rect.right())
        window_rect.moveBottom(screen_rect.bottom() - 50)
        self.floating_window.move(window_rect.topLeft())
        
        # 股票名称缓存（用于搜索）
        self.stock_cache = {}
        self.load_stock_list() # 加载股票列表
        
        # 创建系统托盘图标
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.setToolTip(f"{self.stock_name}: {self.current_price}")
        
        # 创建托盘菜单
        self.menu = QMenu()
        self.menu.setMinimumWidth(180)
        
        # 添加股票信息区域
        self.stock_info_container = QLabel()
        self.stock_info_container.setMinimumHeight(80)
        self.update_stock_info_label()
        
        # 将信息区域添加到菜单
        label_action = QWidgetAction(self.menu)
        label_action.setDefaultWidget(self.stock_info_container)
        self.menu.addAction(label_action)
        
        # 添加分隔线
        self.menu.addSeparator()
        
        # 添加选择股票选项
        change_stock_action = QAction("选择股票", self.menu)
        change_stock_action.triggered.connect(self.show_stock_dialog)
        self.menu.addAction(change_stock_action)
        
        # 添加刷新选项
        refresh_action = QAction("刷新数据", self.menu)
        refresh_action.triggered.connect(self.refresh_stock_data)
        self.menu.addAction(refresh_action)
        
        # 添加悬浮窗口切换
        self.float_window_action = QAction("隐藏悬浮窗口", self.menu)
        self.float_window_action.triggered.connect(self.toggle_floating_window)
        self.menu.addAction(self.float_window_action)
        
        # 添加设置选项
        settings_action = QAction("设置", self.menu)
        settings_action.triggered.connect(self.show_settings)
        self.menu.addAction(settings_action)
        
        # 添加退出选项
        quit_action = QAction("退出", self.menu)
        quit_action.triggered.connect(self.app.quit)
        self.menu.addAction(quit_action)
        
        # 将菜单设置到托盘图标
        self.tray_icon.setContextMenu(self.menu)
        
        # 初始绘制图标
        self.draw_stock_icon()
        
        # 显示托盘图标
        self.tray_icon.show()
        
        # 创建定时器，实时更新数据(默认3秒)
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_stock_data)
        self.timer.start(DEFAULT_REFRESH_RATE * 1000)
        
        # 初始获取股票数据
        self.refresh_stock_data()
    
    def load_stock_list(self):
        """加载股票列表数据"""
        try:
            # 尝试从本地文件加载股票列表
            try:
                with open('stock_list.json', 'r', encoding='utf-8') as f:
                    self.stock_cache = json.load(f)
                    return
            except (FileNotFoundError, json.JSONDecodeError):
                pass
                
            # 如果本地文件不存在或无效，则创建基本股票列表
            # 包含一些常见的A股股票
            basic_stocks = {
                "600000": "浦发银行", "600001": "邯郸钢铁", "600002": "齐鲁石化", 
                "600003": "ST东北高", "600004": "白云机场", "600005": "武钢股份", 
                "600006": "东风汽车", "600007": "中国国贸", "600008": "首创股份", 
                "600009": "上海机场", "600010": "包钢股份", "600011": "华能国际", 
                "600012": "皖通高速", "600015": "华夏银行", "600016": "民生银行", 
                "600018": "上港集团", "600019": "宝钢股份", "600020": "中原高速", 
                "600021": "上海电力", "600022": "山东钢铁", "600028": "中国石化", 
                "600029": "南方航空", "600030": "中信证券", "600031": "三一重工", 
                "601398": "工商银行", "601288": "农业银行", "601988": "中国银行", 
                "601318": "中国平安", "601857": "中国石油", "600519": "贵州茅台", 
                "601166": "兴业银行", "600036": "招商银行", "600276": "恒瑞医药", 
                "600887": "伊利股份", "601328": "交通银行", "603019": "中科曙光"
            }
            self.stock_cache = basic_stocks
            
            # 保存到本地文件
            with open('stock_list.json', 'w', encoding='utf-8') as f:
                json.dump(self.stock_cache, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"加载股票列表出错: {e}")
            # 如果出错，至少确保有默认股票
            self.stock_cache = {"603019": "中科曙光"}
    
    def update_stock_info_label(self):
        """更新股票信息标签"""
        # 根据涨跌设置颜色
        if self.price_change.startswith("+"):
            price_color = "#F5222D"  # 红色
        else:
            price_color = "#52C41A"  # 绿色
            
        # 判断市场状态颜色
        status_color = "#8C8C8C"  # 默认灰色
        if self.market_status == "交易中":
            status_color = "#1890FF"  # 蓝色
        
        # 更新HTML内容
        self.stock_info_container.setText(
            f"<div style='padding:10px; text-align:center;'>"
            f"<div style='font-size:16px;'><b>{self.stock_name}</b> <span style='color:#8C8C8C; font-size:12px;'>{self.stock_code}</span></div>"
            f"<div style='font-size:26px; margin:5px 0; font-weight:bold;'>{self.current_price}</div>"
            f"<div style='color:{price_color}; font-size:14px;'>{self.price_change} ({self.change_percent})</div>"
            f"<div style='margin-top:6px; font-size:12px;'>"
            f"<span style='color:{status_color};'>{self.market_status}</span> | "
            f"更新: {self.update_time}</div>"
            f"</div>"
        )
    
    def tray_icon_activated(self, reason):
        """处理托盘图标激活事件"""
        if reason == QSystemTrayIcon.Trigger:  # 单击
            # 如果菜单已经显示，则隐藏
            if self.menu.isVisible():
                self.menu.hide()
            else:
                # 显示菜单在鼠标位置
                self.menu.popup(QCursor().pos())
    
    def draw_stock_icon(self):
        """绘制美观的股票图标"""
        # 创建一个18x18的图标
        size = 18
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # 根据股价涨跌决定颜色
        if self.price_change.startswith("+"):
            # 红色渐变 - 上涨
            gradient = QRadialGradient(size/2, size/2, size/2)
            gradient.setColorAt(0, QColor(255, 80, 80))
            gradient.setColorAt(1, QColor(200, 50, 50))
        else:
            # 绿色渐变 - 下跌
            gradient = QRadialGradient(size/2, size/2, size/2)
            gradient.setColorAt(0, QColor(60, 205, 60))
            gradient.setColorAt(1, QColor(40, 160, 40))
        
        # 圆角矩形或圆形背景
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(0, 0, size, size, 5, 5)  # 圆角矩形
        
        # 绘制价格文字
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.setFont(QFont("Arial", 9, QFont.Bold))
        
        # 根据数字长度调整显示方式
        price = float(self.current_price)
        display_text = ""
        
        if price >= 1000:
            display_text = str(int(price/1000))
        elif price >= 100:
            display_text = str(int(price/100))
        elif price >= 10:
            display_text = str(int(price/10))
        else:
            display_text = str(int(price))
        
        # 检查文本宽度是否超出图标宽度
        metrics = QFontMetrics(painter.font())
        text_width = metrics.horizontalAdvance(display_text)
        
        # 如果太宽，减小字体
        if text_width > size-4:
            painter.setFont(QFont("Arial", 7, QFont.Bold))
        
        painter.drawText(pixmap.rect(), Qt.AlignCenter, display_text)
        painter.end()
        
        # 设置图标
        self.tray_icon.setIcon(QIcon(pixmap))
    
    def get_stock_data(self):
        """获取股票数据"""
        try:
            # 使用新浪财经API获取股票数据
            # 上证: sh + 代码, 深证: sz + 代码
            prefix = "sh" if self.stock_code.startswith("6") else "sz"
            url = f"https://hq.sinajs.cn/list={prefix}{self.stock_code}"
            
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://finance.sina.com.cn"
            }
            
            response = requests.get(url, headers=headers)
            response.encoding = 'gbk'  # 设置正确的编码
            
            # 解析返回的数据
            data = response.text.split('"')[1].split(',')
            if len(data) > 3:
                self.stock_name = data[0]
                open_price = float(data[1])  # 开盘价
                yesterclose = float(data[2])  # 昨日收盘价
                self.current_price = data[3]  # 当前价格
                high_price = data[4]  # 最高价
                low_price = data[5]  # 最低价
                
                # 判断市场状态
                now = datetime.now()
                today_930 = now.replace(hour=9, minute=30, second=0)
                today_1130 = now.replace(hour=11, minute=30, second=0)
                today_1300 = now.replace(hour=13, minute=0, second=0)
                today_1500 = now.replace(hour=15, minute=0, second=0)
                
                # 交易时间判断
                is_trading_hours = ((now >= today_930 and now <= today_1130) or 
                                  (now >= today_1300 and now <= today_1500))
                
                # 判断是否是周末
                is_weekend = now.weekday() >= 5  # 5=周六，6=周日
                
                if is_weekend:
                    self.market_status = "周末休市"
                elif is_trading_hours:
                    self.market_status = "交易中"
                else:
                    self.market_status = "休市"
                
                # 计算涨跌幅
                price_change = float(self.current_price) - yesterclose
                change_percent = (price_change / yesterclose) * 100
                
                # 格式化数据
                self.price_change = f"+{price_change:.2f}" if price_change >= 0 else f"{price_change:.2f}"
                self.change_percent = f"+{change_percent:.2f}%" if change_percent >= 0 else f"{change_percent:.2f}%"
                
                # 更新时间
                self.update_time = now.strftime("%H:%M:%S")
                
                # 如果股票名称没有在缓存中，添加到缓存中
                if self.stock_code not in self.stock_cache:
                    self.stock_cache[self.stock_code] = self.stock_name
                    # 保存到本地文件
                    try:
                        with open('stock_list.json', 'w', encoding='utf-8') as f:
                            json.dump(self.stock_cache, f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        print(f"保存股票列表失败: {e}")
                
                return True
            return False
        except Exception as e:
            print(f"获取股票数据出错: {e}")
            return False
    
    def toggle_floating_window(self):
        """切换悬浮窗口显示/隐藏状态"""
        if self.floating_window.isVisible():
            self.floating_window.hide()
            self.float_window_action.setText("显示悬浮窗口")
        else:
            self.floating_window.show()
            self.float_window_action.setText("隐藏悬浮窗口")
    
    def refresh_stock_data(self):
        """刷新股票数据"""
        if self.get_stock_data():
            # 更新托盘图标和菜单
            self.update_stock_info_label()
            self.draw_stock_icon()
            
            # 更新悬浮窗口
            self.floating_window.update_stock_info(
                self.stock_code, 
                self.stock_name,
                self.current_price,
                self.price_change,
                self.change_percent
            )
            
            # 更新托盘图标提示
            tooltip = f"{self.stock_name} ({self.stock_code})\n{self.current_price} {self.price_change}\n{self.market_status} | 更新: {self.update_time}"
            self.tray_icon.setToolTip(tooltip)
            
            # 如果涨跌幅超过5%，显示消息通知
            change_percent_value = float(self.change_percent.replace('%', '').replace('+', ''))
            if change_percent_value > 5:
                self.tray_icon.showMessage(
                    f"{self.stock_name} 大幅上涨",
                    f"当前价格: {self.current_price}, 涨幅: {self.change_percent}",
                    QSystemTrayIcon.Information,
                    3000
                )
            elif change_percent_value < -5:
                self.tray_icon.showMessage(
                    f"{self.stock_name} 大幅下跌",
                    f"当前价格: {self.current_price}, 跌幅: {self.change_percent}",
                    QSystemTrayIcon.Warning,
                    3000
                )
    
    def search_stock(self, keyword):
        """根据关键词搜索股票，如果本地未找到则进行在线搜索"""
        results = []
        keyword = keyword.lower()  # 转换为小写进行比较
        found_in_local = False
        
        # 先在本地缓存中搜索
        # 如果输入是股票代码
        if keyword.isdigit():
            for code, name in self.stock_cache.items():
                if code.startswith(keyword):
                    results.append((code, name))
                    # 如果是精确匹配，记录已在本地找到
                    if code == keyword:
                        found_in_local = True
        # 如果输入是股票名称
        else:
            for code, name in self.stock_cache.items():
                if keyword in name.lower():
                    results.append((code, name))
        
        # 如果是股票代码但在本地未找到精确匹配，则从网络搜索
        if keyword.isdigit() and len(keyword) == 6 and not found_in_local:
            try:
                online_result = self.online_search_stock(keyword)
                if online_result:
                    code, name = online_result
                    # 添加到结果开头并标记为网络来源
                    results.insert(0, (code, name))
                    # 添加到缓存
                    self.stock_cache[code] = name
                    # 保存到本地文件
                    try:
                        with open('stock_list.json', 'w', encoding='utf-8') as f:
                            json.dump(self.stock_cache, f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        print(f"保存股票列表失败: {e}")
            except Exception as e:
                print(f"在线搜索股票出错: {e}")
        
        return results[:20]  # 最多返到20个结果
    
    def online_search_stock(self, code):
        """从网络搜索股票信息"""
        # 请求数据
        try:
            # 确定股票市场
            # 上证: sh + 代码, 深证: sz + 代码
            prefix = "sh" if code.startswith("6") else "sz"
            url = f"https://hq.sinajs.cn/list={prefix}{code}"
            
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://finance.sina.com.cn"
            }
            
            response = requests.get(url, headers=headers)
            response.encoding = 'gbk'  # 设置正确的编码
            
            # 解析返回的数据
            data = response.text
            # 检查是否找到结果
            if "FAILED" in data or len(data.split('",')[0].split('="')) < 2:
                # 尝试另一个前缀
                prefix = "sz" if prefix == "sh" else "sh"
                url = f"https://hq.sinajs.cn/list={prefix}{code}"
                response = requests.get(url, headers=headers)
                response.encoding = 'gbk'
                data = response.text
                
            # 再次检查结果
            if "FAILED" in data or len(data.split('",')[0].split('="')) < 2:
                return None
            
            # 提取股票名称
            stock_data = data.split('",')[0].split('="')[1]
            if "," in stock_data and len(stock_data.split(',')) > 0:
                stock_name = stock_data.split(',')[0]
                return (code, stock_name)
                
            return None
        except Exception as e:
            print(f"获取股票数据出错: {e}")
            return None

    def show_stock_dialog(self):
        """显示搜索和选择股票的对话框"""
        dialog = QDialog()
        dialog.setWindowTitle("搜索股票")
        dialog.setMinimumWidth(350)
        dialog.setMinimumHeight(400)
        layout = QVBoxLayout()
        
        # 添加说明标签
        tip_label = QLabel("请输入股票代码或名称进行搜索")
        tip_label.setStyleSheet("margin-bottom: 5px;")
        layout.addWidget(tip_label)
        
        # 创建搜索框
        search_layout = QHBoxLayout()
        search_input = QLineEdit()
        search_input.setPlaceholderText("输入股票代码或名称")
        search_button = QPushButton("搜索")
        search_layout.addWidget(search_input, 7)
        search_layout.addWidget(search_button, 3)
        layout.addLayout(search_layout)
        
        # 创建结果表格
        result_table = QTableWidget(0, 2)  # 0行2列
        result_table.setHorizontalHeaderLabels(["代码", "名称"])
        result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        result_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 不可编辑
        result_table.setSelectionBehavior(QTableWidget.SelectRows)  # 按行选择
        layout.addWidget(result_table)
        
        # 添加分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # 创建按钮区域
        button_layout = QHBoxLayout()
        select_button = QPushButton("选择")
        select_button.setEnabled(False)  # 初始禁用
        cancel_button = QPushButton("取消")
        button_layout.addWidget(select_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # 设置布局
        dialog.setLayout(layout)
        
        # 实现搜索功能
        def perform_search():
            keyword = search_input.text().strip()
            if not keyword:
                return
                
            results = self.search_stock(keyword)
            result_table.setRowCount(len(results))
            
            for i, (code, name) in enumerate(results):
                code_item = QTableWidgetItem(code)
                name_item = QTableWidgetItem(name)
                result_table.setItem(i, 0, code_item)
                result_table.setItem(i, 1, name_item)
            
            if results:
                result_table.selectRow(0)  # 选中第一行
                select_button.setEnabled(True)
            else:
                select_button.setEnabled(False)
        
        # 设置事件
        search_button.clicked.connect(perform_search)
        search_input.returnPressed.connect(perform_search)  # 回车键触发搜索
        
        # 双击选择股票
        def on_table_double_clicked(item):
            row = item.row()
            code = result_table.item(row, 0).text()
            dialog.accept()
            self.change_stock(code, dialog)
        
        result_table.itemDoubleClicked.connect(on_table_double_clicked)
        
        # 选择按钮点击
        def on_select_clicked():
            selected_rows = result_table.selectedItems()
            if selected_rows:
                row = selected_rows[0].row()
                code = result_table.item(row, 0).text()
                dialog.accept()
                self.change_stock(code, dialog)
        
        select_button.clicked.connect(on_select_clicked)
        cancel_button.clicked.connect(dialog.reject)
        
        # 显示对话框
        dialog.exec_()
    
    def change_stock(self, new_code, dialog=None):
        """更改跟踪的股票代码"""
        if new_code and (new_code.startswith("6") or new_code.startswith("0") or new_code.startswith("3")):
            self.stock_code = new_code
            self.refresh_stock_data()
            if dialog:
                dialog.accept()
            return True
        return False
        
    def show_settings(self):
        """显示设置对话框"""
        dialog = QDialog()
        dialog.setWindowTitle("设置")
        dialog.setMinimumWidth(300)
        layout = QVBoxLayout()
        
        # 添加刷新时间设置
        layout.addWidget(QLabel("刷新间隔(秒):"))
        refresh_options = ["10", "30", "60", "120", "300"]
        current_refresh = str(int(self.timer.interval() / 1000))
        
        # 创建按钮组
        button_layout = QHBoxLayout()
        for option in refresh_options:
            btn = QPushButton(option)
            if option == current_refresh:
                btn.setStyleSheet("background-color: #1890FF; color: white;")
            btn.clicked.connect(lambda checked, opt=option: self.set_refresh_interval(int(opt), dialog))
            button_layout.addWidget(btn)
        
        layout.addLayout(button_layout)
        
        # 添加分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # 添加关于信息
        about_label = QLabel(
            "<div style='text-align:center;'>"
            "<p><b>迷你股票行情监控器</b></p>"
            "<p>v1.0.0</p>"
            "<p>简洁的A股股票行情监控小工具</p>"
            "</div>"
        )
        about_label.setStyleSheet("color: #8C8C8C; margin: 10px;")
        layout.addWidget(about_label)
        
        # 确认按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def set_refresh_interval(self, seconds, dialog=None):
        """设置刷新间隔"""
        self.timer.setInterval(seconds * 1000)
        self.refresh_stock_data()
        if dialog:
            dialog.accept()
    
    def run(self):
        """运行应用"""
        # 显示欢迎消息
        self.tray_icon.showMessage(
            "迷你股票监控器",
            f"正在监控: {self.stock_name} ({self.stock_code})\n单击小图标查看详情",
            QSystemTrayIcon.Information,
            3000
        )
        return self.app.exec_()

if __name__ == "__main__":
    try:
        app = StockTrayApp()
        sys.exit(app.run())
    except Exception as e:
        print(f"程序发生错误: {e}")
        # 显示错误对话框
        error_app = QApplication(sys.argv)
        QMessageBox.critical(None, "错误", f"程序运行出错\n{str(e)}")
        sys.exit(1)
