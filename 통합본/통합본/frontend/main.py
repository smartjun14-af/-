import os
import re

from nicegui import app, ui

import api_client
from api_client import ApiError

# =========================
# 세션 단위 로그인 상태 관리
# =========================
# 원본 코드는 모듈 전역 dict(current_user) 하나를 모든 접속자가 공유했기 때문에
# 여러 사용자가 동시에 접속하면 로그인 상태가 뒤섞이는 문제가 있었다.
# NiceGUI 의 app.storage.user 는 브라우저 세션(쿠키)별로 분리 저장되므로
# 이를 사용해 사용자별로 토큰/이메일을 안전하게 보관한다.
# (app.storage.user 사용에는 ui.run(storage_secret=...) 설정이 필요하다.)


def is_logged_in() -> bool:
    return bool(app.storage.user.get('access_token'))


def current_email() -> str:
    return app.storage.user.get('email', '')


def get_token() -> str:
    return app.storage.user.get('access_token', '')


def get_refresh_token() -> str:
    return app.storage.user.get('refresh_token', '')


def set_session(email: str, access_token: str, refresh_token: str) -> None:
    app.storage.user['email'] = email
    app.storage.user['access_token'] = access_token
    app.storage.user['refresh_token'] = refresh_token


def clear_session() -> None:
    app.storage.user['email'] = ''
    app.storage.user['access_token'] = ''
    app.storage.user['refresh_token'] = ''


def do_logout() -> None:
    """백엔드에 refresh 토큰 폐기를 요청하고(실패해도 무시) 세션을 비운 뒤 로그인 화면으로 이동."""
    refresh_token = get_refresh_token()
    if refresh_token:
        try:
            api_client.logout(refresh_token)
        except ApiError:
            pass  # 로그아웃은 best-effort: 서버 오류와 무관하게 로컬 세션은 정리한다.
    clear_session()
    ui.notify('로그아웃되었습니다.', type='positive')
    ui.navigate.to('/')


#헤더
def header():
    with ui.header().classes('bg-white text-[#1E293B] shadow-md border-b border-[#E2E8F0]'):
        with ui.row().classes('items-center gap-6 w-full px-6'):
            ui.label('COIN').classes('text-2xl font-bold text-[#2563EB] tracking-wide')

            ui.link('대시보드', '/dashboard').classes('text-[#475569] no-underline hover:text-[#2563EB]')
            ui.link('수동매매', '/manual-trade').classes('text-[#475569] no-underline hover:text-[#2563EB]')
            ui.link('자동매매', '/auto-trade').classes('text-[#475569] no-underline hover:text-[#2563EB]')
            ui.link('백테스팅', '/backtest').classes('text-[#475569] no-underline hover:text-[#2563EB]')
            ui.link('포트폴리오', '/portfolio').classes('text-[#475569] no-underline hover:text-[#2563EB]')
            ui.link('입출금', '/deposit').classes('text-[#475569] no-underline hover:text-[#2563EB]')
            ui.link('설정', '/settings').classes('text-[#475569] no-underline hover:text-[#2563EB]')

            ui.space()

            ui.button(
                '로그아웃',
                on_click=do_logout,
            ).props('flat').classes('text-[#EF4444] no-underline hover:text-[#DC2626]')


# 로그인 페이지
@ui.page('/')
def login_page():
    ui.colors(primary='#2563EB')

    with ui.column().classes(
        'w-full min-h-screen bg-white text-[#222222] items-center justify-center px-6'
    ):
        ui.label('COIN').classes('text-6xl font-black text-[#2563EB] mb-10')

        container = ui.column().classes('w-full items-center')

        def render_login():
            container.clear()

            with container:
                with ui.card().classes(
                    'w-[560px] bg-white border border-[#E5E7EB] rounded-2xl shadow-lg p-10'
                ):
                    ui.label('로그인').classes('text-3xl font-bold mb-6 text-[#222222]')

                    email = ui.input(
                        placeholder='이메일주소'
                    ).props(
                        'outlined autocomplete=off'
                    ).classes(
                        'w-full mb-3'
                    )

                    password = ui.input(
                        placeholder='비밀번호',
                        password=True,
                        password_toggle_button=True
                    ).props(
                        'outlined autocomplete=new-password'
                    ).classes(
                        'w-full'
                    )

                    with ui.row().classes('w-full items-center justify-between mt-2 mb-6'):
                        ui.checkbox('로그인 상태 유지').classes('text-[#666666]')

                    def login():
                        if not email.value:
                            ui.notify('이메일을 입력해주세요.', type='warning')
                            return
                    
                        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
                        if not re.match(email_pattern, email.value):
                            ui.notify('올바른 이메일 형식을 입력해주세요. 예: user@email.com', type='warning')
                            return

                        if not password.value:
                            ui.notify('비밀번호를 입력해주세요.', type='warning')
                            return

                        try:
                            result = api_client.login(email.value, password.value)
                        except ApiError as e:
                            ui.notify(e.message, type='negative')
                            return

                        set_session(result['email'], result['access_token'], result['refresh_token'])
                        ui.notify('로그인 성공', type='positive')
                        ui.navigate.to('/dashboard')
                        

                    ui.button(
                        '로그인',
                        on_click=login
                    ).classes(
                        'w-full bg-[#2563EB] font-bold rounded-lg py-4 text-lg mb-6 shadow-md'
                    ).style(
                        'color:#FFFFFF !important;'
                    )

                    ui.separator().classes('mb-6')

                    ui.button(
                        '회원가입',
                        on_click=render_signup
                    ).classes(
                        'w-full bg-white border border-[#2563EB] font-bold rounded-lg py-4 text-lg'
                    ).style(
                        'color:#2563EB !important;'
                    )


        def render_signup():
            container.clear()

            with container:
                with ui.card().classes(
                    'w-[560px] bg-white border border-[#E5E7EB] rounded-2xl shadow-lg p-10'
                ):
                    ui.label('회원가입').classes('text-3xl font-bold mb-6 text-[#222222]')

                    email = ui.input(
                        placeholder='이메일'
                    ).props(
                        'outlined autocomplete=off'
                    ).classes(
                        'w-full mb-3'
                    )

                    password = ui.input(
                        placeholder='비밀번호',
                        password=True,
                        password_toggle_button=True
                    ).props(
                        'outlined autocomplete=new-password'
                    ).classes(
                        'w-full mb-2'
                    )

                    password_confirm = ui.input(
                        placeholder='비밀번호 확인',
                        password=True,
                        password_toggle_button=True
                    ).props(
                        'outlined autocomplete=new-password'
                    ).classes(
                        'w-full mb-2'
                    )

                    # NiceGUI 기본 비밀번호 토글 버튼
                    password.props('clearable')
                    password_confirm.props('clearable')


                    def register():
                        if not email.value:
                            ui.notify('이메일을 입력해주세요.', type='warning')
                            return

                        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
                        if not re.match(email_pattern, email.value):
                            ui.notify('올바른 이메일 형식을 입력해주세요. 예: user@email.com', type='warning')
                            return

                        if not password.value:
                            ui.notify('비밀번호를 입력해주세요.', type='warning')
                            return

                        if len(password.value) < 8:
                            ui.notify('비밀번호는 8자 이상이어야 합니다.', type='warning')
                            return

                        if not password_confirm.value:
                            ui.notify('비밀번호 확인을 입력해주세요.', type='warning')
                            return

                        if password.value != password_confirm.value:
                            ui.notify('비밀번호와 비밀번호 확인이 일치하지 않습니다.', type='negative')
                            return

                        try:
                            api_client.register(email.value, password.value)
                        except ApiError as e:
                            ui.notify(e.message, type='negative')
                            return

                        ui.notify('계정 생성이 완료되었습니다. 로그인 화면으로 이동합니다.', type='positive')
                        render_login()

                    ui.button(
                        '계정 생성',
                        on_click=register
                    ).classes(
                        'w-full bg-[#2563EB] font-bold rounded-lg py-4 text-lg mb-4 shadow-md'
                    ).style(
                        'color:#FFFFFF !important;'
                    )

                    ui.button(
                        '로그인으로 돌아가기',
                        on_click=render_login
                    ).classes(
                        'w-full bg-white border border-[#BFDBFE] font-bold rounded-lg py-3'
                    ).style(
                        'color:#2563EB !important;'
                    )
        render_login()


@ui.page('/dashboard')
def dashboard_page():
    if not is_logged_in():
        ui.navigate.to('/')
        return

    header()

    # 백엔드에서 대시보드 데이터 조회 (자산 요약 + 코인 시세 + 최근 입출금 내역)
    try:
        data = api_client.get_dashboard(get_token())
    except ApiError as e:
        if e.status == 401:
            # 토큰 만료/무효 → 세션 정리 후 로그인 화면으로
            clear_session()
            ui.notify('세션이 만료되었습니다. 다시 로그인해주세요.', type='warning')
            ui.navigate.to('/')
            return
        # 연결 실패 등 → 오류 안내 + 다시 시도 버튼
        with ui.column().classes('w-full min-h-screen bg-[#F8FAFC] text-[#1E293B] p-8 gap-6'):
            with ui.card().classes('w-full bg-white border border-[#FECACA] rounded-2xl shadow-lg p-8'):
                ui.label('대시보드를 불러오지 못했습니다').classes('text-2xl font-bold text-[#EF4444]')
                ui.label(e.message).classes('text-[#64748B] mb-4')
                ui.button(
                    '다시 시도', on_click=lambda: ui.navigate.to('/dashboard')
                ).classes('bg-[#2563EB] font-bold rounded-lg px-5 py-2').style('color:#FFFFFF !important;')
        return

    summary = data.get('summary', {})
    coins = data.get('coins', [])
    transactions = data.get('recent_transactions', [])

    def fmt_dt(iso_str):
        # "2026-06-03T16:03:56.4..." → "2026-06-03 16:03" (UTC 기준)
        if not iso_str:
            return ''
        return iso_str.replace('T', ' ')[:16]

    def format_won(value):
        return f'{value:,.0f}원'

    with ui.column().classes('w-full min-h-screen bg-[#F8FAFC] text-[#1E293B] p-8 gap-6'):
        with ui.row().classes('items-end justify-between w-full'):
            with ui.column().classes('gap-1'):
                ui.label('대시보드').classes('text-4xl font-bold text-[#1E293B]')
                ui.label('실시간 자산 현황과 자동매매 상태를 확인합니다.').classes('text-[#64748B]')

            ui.button('새로고침', on_click=lambda: ui.notify('데이터를 새로고침했습니다.', type='positive')).classes(
                'bg-[#2563EB] font-bold rounded-lg px-5 py-2 shadow-md'
            ).style('color:#FFFFFF !important;')

        with ui.row().classes('gap-4 w-full'):
            cards = [
                ('총 평가금액', format_won(summary['total_asset']), f"{summary['profit_rate']:+.1f}% 오늘", '#2563EB'),
                ('보유 원화', format_won(summary['krw']), '주문 가능 금액', '#0F172A'),
                ('코인 평가액', format_won(summary['coin_value']), 'BTC / ETH / XRP', '#0F172A'),
                ('자동매매 상태', summary['auto_status'], '전략 대기 중', '#EF4444'),
            ]

            for title, value, subtitle, color in cards:
                with ui.card().classes('w-1/4 bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-5'):
                    ui.label(title).classes('text-sm text-[#64748B]')
                    ui.label(value).classes('text-2xl font-bold').style(f'color:{color};')
                    ui.label(subtitle).classes('text-[#64748B] text-sm')

        with ui.row().classes('gap-6 w-full items-start'):
            with ui.card().classes('w-1/3 bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-6'):
                ui.label('주요 코인 시세').classes('text-2xl font-bold text-[#1E293B]')
                ui.label('관심 코인의 현재가와 등락률입니다.').classes('text-[#64748B] text-sm mb-4')

                with ui.row().classes('w-full bg-[#EFF6FF] text-[#2563EB] rounded-lg px-4 py-3 font-bold'):
                    ui.label('코인').classes('w-1/3')
                    ui.label('현재가').classes('w-1/3')
                    ui.label('등락률').classes('w-1/3')

                coin_labels = {}

                for item in coins:
                    rate_color = '#2563EB' if item['rate'] >= 0 else '#EF4444'
                    with ui.row().classes('w-full items-center border-b border-[#E2E8F0] px-4 py-3'):
                        ui.label(item['coin']).classes('w-1/3 font-bold text-[#1E293B]')
                        price_lbl = ui.label(format_won(item['price'])).classes('w-1/3 text-[#334155]')
                        rate_lbl =ui.label(f"{item['rate']:+.2f}%").classes('w-1/3 font-bold').style(f'color:{rate_color};')
                    coin_labels[item['coin']] = {'price': price_lbl, 'rate': rate_lbl}

                async def refresh_prices():
                    try:
                        fresh = api_client.get_dashboard(get_token())
                        for coin in fresh.get('coins', []):
                            if coin['coin'] in coin_labels:
                                coin_labels[coin['coin']]['price'].set_text(format_won(coin['price']))
                                c = '#2563EB' if coin['rate'] >= 0 else '#EF4444'
                                coin_labels[coin['coin']]['rate'].set_text(f"{coin['rate']:+.2f}%")
                                coin_labels[coin['coin']]['rate'].style(f'color:{c};')
                    except ApiError:
                        pass

                ui.timer(0.5, refresh_prices)
                ui.timer(2.0, lambda: load_chart(chart_state['coin']))

                ui.label('시세 차트').classes('text-2xl font-bold text-[#1E293B]')
                ui.label('선택 코인의 1일(60분봉) 시세 흐름입니다.').classes('text-[#64748B] text-sm mb-4')

                chart_coins = ['BTC', 'ETH', 'XRP']
                chart_state = {'coin': 'BTC'}
                chart_buttons = {}

                with ui.row().classes('gap-2 mb-4'):
                    for _c in chart_coins:
                        chart_buttons[_c] = ui.button(
                            _c, on_click=lambda c=_c: load_chart(c)
                        ).classes('bg-[#DBEAFE] border border-[#BFDBFE] font-bold rounded-lg px-4').style('color:#2563EB !important;')

                chart = ui.echart({
                    'tooltip': {'trigger': 'axis'},
                    'grid': {'left': 60, 'right': 16, 'top': 20, 'bottom': 30},
                    'xAxis': {'type': 'category', 'boundaryGap': False, 'data': [], 'axisLabel': {'color': '#64748B'}},
                    'yAxis': {'type': 'value', 'scale': True, 'axisLabel': {'color': '#64748B'}, 'splitLine': {'lineStyle': {'color': '#E2E8F0'}}},
                    'series': [{'name': 'BTC', 'type': 'line', 'smooth': True, 'showSymbol': False, 'data': [], 'lineStyle': {'color': '#2563EB', 'width': 2}, 'areaStyle': {'color': 'rgba(37,99,235,0.12)'}}],
                }).classes('w-full h-64')

                def style_chart_buttons():
                    for c, btn in chart_buttons.items():
                        if c == chart_state['coin']:
                            btn.classes(replace='bg-[#2563EB] font-bold rounded-lg px-4')
                            btn.style(replace='color:#FFFFFF !important;')
                        else:
                            btn.classes(replace='bg-[#DBEAFE] border border-[#BFDBFE] font-bold rounded-lg px-4')
                            btn.style(replace='color:#2563EB !important;')

                def load_chart(coin):
                    chart_state['coin'] = coin
                    style_chart_buttons()
                    try:
                        cdata = api_client.get_candles(get_token(), coin, interval='minute60', count=24)
                    except ApiError as e:
                        ui.notify(f'{coin} 차트를 불러오지 못했습니다: {e.message}', type='negative')
                        return
                    candles = cdata.get('candles', [])
                    chart.options['xAxis']['data'] = [c['time'][11:16] for c in candles]
                    chart.options['series'][0]['data'] = [c['close'] for c in candles]
                    chart.options['series'][0]['name'] = coin
                    chart.update()

                style_chart_buttons()
                load_chart('BTC')

            with ui.card().classes('w-1/3 bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-6'):
                ui.label('최근 입출금 내역').classes('text-2xl font-bold text-[#1E293B]')
                ui.label('최근 처리된 가상 원화 입출금 기록입니다.').classes('text-[#64748B] text-sm mb-4')

                if not transactions:
                    with ui.element('div').classes(
                        'w-full h-32 flex items-center justify-center bg-[#F1F5F9] rounded-xl border border-[#E2E8F0] text-[#64748B]'
                    ):
                        ui.label('아직 입출금 내역이 없습니다.')
                else:
                    for item in transactions:
                        is_deposit = item.get('transaction_type') == 'DEPOSIT'
                        label_text = '입금' if is_deposit else '출금'
                        type_color = '#2563EB' if is_deposit else '#EF4444'
                        with ui.row().classes('w-full items-center justify-between border-b border-[#E2E8F0] py-3'):
                            ui.label(label_text).classes('font-bold').style(f'color:{type_color};')
                            ui.label(format_won(item.get('amount', 0))).classes('text-[#334155]')
                            ui.label(fmt_dt(item.get('created_at'))).classes('text-[#64748B] text-sm')

                ui.button(
                    '입출금 바로가기',
                    on_click=lambda: ui.navigate.to('/deposit')
                ).classes('w-full bg-[#DBEAFE] border border-[#BFDBFE] font-bold rounded-lg py-3 mt-4').style('color:#2563EB !important;')

@ui.page('/manual-trade')
def manual_trade_page():
    if not is_logged_in():
        ui.navigate.to('/')
        return

    header()

    selected_coin = {'value': 'BTC'}
    order_mode = {'side': '매수', 'type': '지정가'}

    coins = [
        {'coin': 'BTC', 'price': 98500000, 'rate': 2.15},
        {'coin': 'ETH', 'price': 4200000, 'rate': -0.85},
        {'coin': 'XRP', 'price': 820, 'rate': 1.02},
        {'coin': 'SOL', 'price': 242000, 'rate': 3.34},
    ]

    asks = [98600000, 98550000, 98500000]
    bids = [98450000, 98400000, 98350000]
    pending_orders = [
        {'coin': 'BTC', 'side': '매수', 'type': '지정가', 'price': 97000000, 'quantity': 0.01},
        {'coin': 'ETH', 'side': '매도', 'type': '지정가', 'price': 4300000, 'quantity': 0.2},
    ]

    def format_won(value):
        return f'{value:,.0f}원'

    with ui.column().classes('w-full min-h-screen bg-[#F8FAFC] text-[#1E293B] p-8 gap-6'):
        with ui.column().classes('gap-1'):
            ui.label('수동매매').classes('text-4xl font-bold text-[#1E293B]')
            ui.label('코인을 선택하고 지정가 또는 시장가 주문을 생성합니다.').classes('text-[#64748B]')

        with ui.row().classes('gap-6 w-full items-start'):
            with ui.card().classes('w-1/5 bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-5'):
                ui.label('코인 목록').classes('text-2xl font-bold text-[#1E293B]')
                ui.input(placeholder='코인 검색').props('outlined autocomplete=off').classes('w-full my-4').style('background:#FFFFFF; border-radius:10px; color:#1E293B;')

                for item in coins:
                    rate_color = '#2563EB' if item['rate'] >= 0 else '#EF4444'

                    def select_coin(coin=item['coin']):
                        selected_coin['value'] = coin
                        ui.notify(f'{coin} 선택됨', type='positive')

                    with ui.row().classes('w-full items-center justify-between border-b border-[#E2E8F0] py-3 cursor-pointer').on('click', select_coin):
                        ui.label(item['coin']).classes('font-bold')
                        with ui.column().classes('items-end gap-0'):
                            ui.label(format_won(item['price'])).classes('text-[#334155] text-sm')
                            ui.label(f"{item['rate']:+.2f}%").classes('font-bold text-sm').style(f'color:{rate_color};')

            with ui.card().classes('w-2/5 bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-6'):
                ui.label('시세 / 차트').classes('text-2xl font-bold text-[#1E293B]')
                ui.label('선택 코인의 캔들 차트와 미체결 주문입니다.').classes('text-[#64748B] text-sm mb-4')

                with ui.row().classes('gap-2 mb-4'):
                    for label in ['1분', '10분', '30분', '1시간', '일']:
                        ui.button(label).classes('bg-[#DBEAFE] border border-[#BFDBFE] font-bold rounded-lg px-3').style('color:#2563EB !important;')

                with ui.element('div').classes('w-full h-72 flex items-center justify-center bg-[#EFF6FF] border border-[#BFDBFE] rounded-2xl text-[#2563EB] mb-6'):
                    ui.label('캔들 차트 영역').classes('font-bold')

                ui.label('미체결 주문').classes('text-xl font-bold text-[#1E293B] mb-2')
                if not pending_orders:
                    ui.label('미체결 주문이 없습니다.').classes('text-[#64748B]')
                else:
                    for item in pending_orders:
                        with ui.row().classes('w-full items-center justify-between border-b border-[#E2E8F0] py-3'):
                            ui.label(item['coin']).classes('font-bold')
                            ui.label(item['side']).classes('font-bold').style('color:#2563EB;' if item['side'] == '매수' else 'color:#EF4444;')
                            ui.label(item['type']).classes('text-[#334155]')
                            ui.label(format_won(item['price'])).classes('text-[#334155]')
                            ui.label(str(item['quantity'])).classes('text-[#64748B]')
                            ui.button('취소', on_click=lambda: ui.notify('주문이 취소되었습니다.', type='warning')).classes('bg-[#FEE2E2] border border-[#FECACA] font-bold rounded-lg px-3').style('color:#EF4444 !important;')

            with ui.card().classes('w-1/5 bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-5'):
                ui.label('호가창').classes('text-2xl font-bold text-[#1E293B]')
                ui.label('매도/매수 호가를 선택하면 주문가격에 반영됩니다.').classes('text-[#64748B] text-sm mb-4')

                price_input = ui.input(placeholder='주문 가격').props('outlined type=number').classes('w-full mb-3').style('background:#FFFFFF; border-radius:10px; color:#1E293B;')

                ui.label('매도 호가').classes('text-[#EF4444] font-bold mb-2')
                for price in asks:
                    ui.button(format_won(price), on_click=lambda p=price: setattr(price_input, 'value', str(p))).classes('w-full bg-[#FEE2E2] border border-[#FECACA] rounded-lg font-bold mb-2').style('color:#EF4444 !important;')

                ui.separator().classes('my-3 bg-[#E2E8F0]')
                ui.label('매수 호가').classes('text-[#2563EB] font-bold mb-2')
                for price in bids:
                    ui.button(format_won(price), on_click=lambda p=price: setattr(price_input, 'value', str(p))).classes('w-full bg-[#DBEAFE] border border-[#BFDBFE] rounded-lg font-bold mb-2').style('color:#2563EB !important;')

            with ui.card().classes('w-1/5 bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-5'):
                ui.label('주문 패널').classes('text-2xl font-bold text-[#1E293B]')
                ui.label('보유 원화: 7,500,000원').classes('text-[#64748B] text-sm mb-4')

                side_toggle = ui.toggle(['매수', '매도'], value='매수').classes('w-full mb-3').props('spread')
                type_toggle = ui.toggle(['지정가', '시장가'], value='지정가').classes('w-full mb-3').props('spread')

                order_price = ui.input(placeholder='주문 가격').props('outlined type=number').classes('w-full mb-3').style('background:#FFFFFF; border-radius:10px; color:#1E293B;')
                quantity = ui.input(placeholder='수량').props('outlined type=number').classes('w-full mb-3').style('background:#FFFFFF; border-radius:10px; color:#1E293B;')

                with ui.grid(columns=3).classes('gap-2 w-full mb-4'):
                    for label in ['10%', '25%', '50%', '75%', '최대']:
                        ui.button(label, on_click=lambda l=label: ui.notify(f'{l} 비율 적용', type='positive')).classes('bg-[#DBEAFE] border border-[#BFDBFE] rounded-lg font-bold').style('color:#2563EB !important;')

                def submit_order():
                    if type_toggle.value == '지정가' and not order_price.value:
                        ui.notify('주문 가격을 입력해주세요.', type='warning')
                        return
                    if not quantity.value:
                        ui.notify('수량을 입력해주세요.', type='warning')
                        return
                    ui.notify(f'{side_toggle.value} 주문이 접수되었습니다.', type='positive')

                ui.button('주문하기', on_click=submit_order).classes('w-full bg-[#2563EB] font-bold rounded-lg py-3').style('color:#FFFFFF !important;')


@ui.page('/auto-trade')
def auto_trade_page():
    if not is_logged_in():
        ui.navigate.to('/')
        return

    header()

    signals = [
        {'time': '14:20', 'coin': 'BTC', 'signal': '대기', 'rsi': 48.2},
        {'time': '13:50', 'coin': 'ETH', 'signal': '매수 신호', 'rsi': 29.8},
        {'time': '12:40', 'coin': 'XRP', 'signal': '익절 감시', 'rsi': 61.5},
    ]

    executions = [
        {'coin': 'ETH', 'type': '매수', 'price': 3900000, 'date': '2026-05-13 13:50'},
        {'coin': 'BTC', 'type': '매도', 'price': 98200000, 'date': '2026-05-12 16:10'},
    ]

    def format_won(value):
        return f'{value:,.0f}원'

    with ui.column().classes('w-full min-h-screen bg-[#F8FAFC] text-[#1E293B] p-8 gap-6'):
        with ui.column().classes('gap-1'):
            ui.label('자동매매').classes('text-4xl font-bold text-[#1E293B]')
            ui.label('전략을 선택하고 조건에 따라 자동 주문을 실행합니다.').classes('text-[#64748B]')

        with ui.row().classes('gap-6 w-full items-start'):
            with ui.card().classes('w-1/3 bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-6'):
                ui.label('전략 설정').classes('text-2xl font-bold text-[#1E293B]')
                ui.label('대상 코인과 RSI 전략 파라미터를 설정합니다.').classes('text-[#64748B] text-sm mb-4')

                strategy = ui.radio(['RSI 역추세', 'MA 추세추종'], value='RSI 역추세').classes('text-[#334155] mb-4')
                coin = ui.select(['BTC', 'ETH', 'XRP', 'SOL'], value='BTC', label='대상 코인').classes('w-full mb-3')
                rsi_period = ui.input(placeholder='RSI 기간 예: 14').props('outlined type=number').classes('w-full mb-3').style('background:#FFFFFF; border-radius:10px; color:#1E293B;')
                overbought = ui.input(placeholder='과매수 기준 예: 70').props('outlined type=number').classes('w-full mb-3').style('background:#FFFFFF; border-radius:10px; color:#1E293B;')
                oversold = ui.input(placeholder='과매도 기준 예: 30').props('outlined type=number').classes('w-full mb-3').style('background:#FFFFFF; border-radius:10px; color:#1E293B;')
                max_invest = ui.input(placeholder='최대 투자금').props('outlined type=number').classes('w-full mb-3').style('background:#FFFFFF; border-radius:10px; color:#1E293B;')
                stop_loss = ui.input(placeholder='손절 기준 예: -3').props('outlined type=number').classes('w-full mb-3').style('background:#FFFFFF; border-radius:10px; color:#1E293B;')
                take_profit = ui.input(placeholder='익절 기준 예: 5').props('outlined type=number').classes('w-full mb-4').style('background:#FFFFFF; border-radius:10px; color:#1E293B;')

                def save_strategy():
                    if not max_invest.value:
                        ui.notify('최대 투자금을 입력해주세요.', type='warning')
                        return
                    ui.notify('전략 설정이 저장되었습니다.', type='positive')

                ui.button('저장·적용', on_click=save_strategy).classes('w-full bg-[#2563EB] font-bold rounded-lg py-3').style('color:#FFFFFF !important;')

            with ui.card().classes('w-1/3 bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-6'):
                ui.label('신호 모니터링').classes('text-2xl font-bold text-[#1E293B]')
                ui.label('전략 신호와 자동매매 ON/OFF 상태를 확인합니다.').classes('text-[#64748B] text-sm mb-4')

                auto_switch = ui.switch('자동매매 ON/OFF', value=False).classes('text-[#334155] mb-4')
                status_label = ui.label('현재 상태: OFF').classes('text-[#EF4444] font-bold mb-4')

                def update_status():
                    if auto_switch.value:
                        status_label.text = '현재 상태: ON'
                        status_label.classes(replace='text-[#2563EB] font-bold mb-4')
                        ui.notify('자동매매가 활성화되었습니다.', type='positive')
                    else:
                        status_label.text = '현재 상태: OFF'
                        status_label.classes(replace='text-[#EF4444] font-bold mb-4')
                        ui.notify('자동매매가 비활성화되었습니다.', type='warning')

                auto_switch.on('update:model-value', lambda _: update_status())

                with ui.row().classes('w-full bg-[#EFF6FF] text-[#2563EB] rounded-lg px-4 py-3 font-bold'):
                    ui.label('시간').classes('w-1/4')
                    ui.label('코인').classes('w-1/4')
                    ui.label('신호').classes('w-1/4')
                    ui.label('RSI').classes('w-1/4')

                for item in signals:
                    signal_color = '#2563EB' if '매수' in item['signal'] else '#EF4444' if '매도' in item['signal'] else '#64748B'
                    with ui.row().classes('w-full items-center border-b border-[#E2E8F0] px-4 py-3'):
                        ui.label(item['time']).classes('w-1/4 text-[#64748B]')
                        ui.label(item['coin']).classes('w-1/4 font-bold')
                        ui.label(item['signal']).classes('w-1/4 font-bold').style(f'color:{signal_color};')
                        ui.label(str(item['rsi'])).classes('w-1/4 text-[#334155]')

            with ui.card().classes('w-1/3 bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-6'):
                ui.label('체결 내역 / 알림').classes('text-2xl font-bold text-[#1E293B]')
                ui.label('자동매매 체결 결과와 주요 알림입니다.').classes('text-[#64748B] text-sm mb-4')

                for item in executions:
                    type_color = '#2563EB' if item['type'] == '매수' else '#EF4444'
                    with ui.row().classes('w-full items-center justify-between border-b border-[#E2E8F0] py-3'):
                        ui.label(item['coin']).classes('font-bold')
                        ui.label(item['type']).classes('font-bold').style(f'color:{type_color};')
                        ui.label(format_won(item['price'])).classes('text-[#334155]')
                        ui.label(item['date']).classes('text-[#64748B] text-sm')

                ui.separator().classes('my-5 bg-[#E2E8F0]')
                ui.label('알림 센터').classes('text-xl font-bold text-[#1E293B] mb-2')

                with ui.element('div').classes('w-full bg-[#EFF6FF] border border-[#BFDBFE] rounded-xl p-4 text-[#2563EB]'):
                    ui.label('RSI 과매도 구간 진입 시 매수 알림이 표시됩니다.').classes('font-bold')

                ui.button('알림 설정으로 이동', on_click=lambda: ui.navigate.to('/settings')).classes('w-full bg-[#DBEAFE] border border-[#BFDBFE] font-bold rounded-lg py-3 mt-4').style('color:#2563EB !important;')


@ui.page('/backtest')
def backtest_page():
    if not is_logged_in():
        ui.navigate.to('/')
        return

    header()

    result_visible = {'value': False}

    def format_won(value):
        return f'{value:,.0f}원'

    with ui.column().classes('w-full min-h-screen bg-[#F8FAFC] text-[#1E293B] p-8 gap-6'):
        with ui.column().classes('gap-1'):
            ui.label('백테스팅').classes('text-4xl font-bold text-[#1E293B]')
            ui.label('과거 데이터를 기반으로 전략 성과를 검증합니다.').classes('text-[#64748B]')

        with ui.row().classes('gap-6 w-full items-start'):
            with ui.card().classes('w-1/4 bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-6'):
                ui.label('백테스팅 설정').classes('text-2xl font-bold text-[#1E293B]')
                ui.label('기간, 코인, 전략 조건을 입력합니다.').classes('text-[#64748B] text-sm mb-4')

                start_date = ui.input(placeholder='시작일 예: 2025-05-01').props('outlined').classes('w-full mb-3').style('background:#FFFFFF; border-radius:10px; color:#1E293B;')
                end_date = ui.input(placeholder='종료일 예: 2026-05-01').props('outlined').classes('w-full mb-3').style('background:#FFFFFF; border-radius:10px; color:#1E293B;')
                coin = ui.select(['BTC', 'ETH', 'XRP', 'SOL'], value='BTC', label='대상 코인').classes('w-full mb-3')
                strategy = ui.select(['RSI 역추세', 'MA 추세추종'], value='RSI 역추세', label='전략').classes('w-full mb-3')
                initial_cash = ui.input(placeholder='초기 투자금').props('outlined type=number').classes('w-full mb-3').style('background:#FFFFFF; border-radius:10px; color:#1E293B;')
                fee = ui.input(placeholder='수수료율 예: 0.05').props('outlined type=number').classes('w-full mb-4').style('background:#FFFFFF; border-radius:10px; color:#1E293B;')

                progress = ui.linear_progress(0).classes('w-full mb-3')
                progress_label = ui.label('진행률: 대기 중').classes('text-[#64748B] text-sm mb-4')

                result_area = ui.column().classes('w-full')

                def render_result():
                    result_area.clear()
                    with result_area:
                        with ui.card().classes('w-full bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-6 mt-6'):
                            ui.label('백테스팅 결과').classes('text-2xl font-bold text-[#1E293B]')
                            ui.label('전략 실행 결과 요약입니다.').classes('text-[#64748B] text-sm mb-4')

                            metrics = [
                                ('수익률', '+12.40%', '#2563EB'),
                                ('MDD', '-5.80%', '#EF4444'),
                                ('승률', '62%', '#2563EB'),
                                ('Sharpe', '1.42', '#0F172A'),
                                ('거래횟수', '34회', '#0F172A'),
                                ('최종자산', format_won(11240000), '#2563EB'),
                            ]

                            with ui.grid(columns=3).classes('gap-4 w-full'):
                                for title, value, color in metrics:
                                    with ui.card().classes('bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-4'):
                                        ui.label(title).classes('text-[#64748B] text-sm')
                                        ui.label(value).classes('text-2xl font-bold').style(f'color:{color};')

                            with ui.element('div').classes('w-full h-72 flex items-center justify-center bg-[#EFF6FF] border border-[#BFDBFE] rounded-2xl text-[#2563EB] mt-6'):
                                ui.label('수익 곡선 차트 영역').classes('font-bold')

                            ui.button('결과 저장', on_click=lambda: ui.notify('백테스팅 결과가 저장되었습니다.', type='positive')).classes('bg-[#2563EB] font-bold rounded-lg px-5 py-2 mt-4').style('color:#FFFFFF !important;')

                def run_backtest():
                    if not start_date.value or not end_date.value:
                        ui.notify('시작일과 종료일을 입력해주세요.', type='warning')
                        return
                    if not initial_cash.value:
                        ui.notify('초기 투자금을 입력해주세요.', type='warning')
                        return
                    progress.value = 1
                    progress_label.text = '진행률: 100% — 완료'
                    ui.notify('백테스팅이 완료되었습니다.', type='positive')
                    render_result()

                ui.button('백테스팅 실행', on_click=run_backtest).classes('w-full bg-[#2563EB] font-bold rounded-lg py-3').style('color:#FFFFFF !important;')

            with ui.column().classes('w-3/4 gap-6'):
                result_area = ui.column().classes('w-full')

                with ui.card().classes('w-full bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-6'):
                    ui.label('전략 비교').classes('text-2xl font-bold text-[#1E293B]')
                    ui.label('여러 전략을 같은 조건으로 비교합니다.').classes('text-[#64748B] text-sm mb-4')

                    with ui.row().classes('gap-4 w-full'):
                        compare_cards = [
                            ('RSI 역추세', '+12.40%', '-5.80%', '62%'),
                            ('MA 추세추종', '+8.20%', '-7.10%', '55%'),
                            ('볼린저밴드', '+10.10%', '-6.30%', '59%'),
                        ]

                        for name, rate, mdd, win in compare_cards:
                            with ui.card().classes('w-1/3 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-4'):
                                ui.label(name).classes('text-lg font-bold text-[#1E293B]')
                                ui.label(f'수익률 {rate}').classes('text-[#2563EB] font-bold mt-2')
                                ui.label(f'MDD {mdd}').classes('text-[#EF4444] font-bold')
                                ui.label(f'승률 {win}').classes('text-[#334155]')

                with ui.card().classes('w-full bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-6'):
                    ui.label('안내').classes('text-2xl font-bold text-[#1E293B]')
                    ui.label('현재는 프론트 더미 데이터로 동작합니다. 백엔드 연동 후 실제 과거 시세 데이터를 기반으로 계산합니다.').classes('text-[#64748B]')


@ui.page('/portfolio')
def portfolio_page():
    if not is_logged_in():
        ui.navigate.to('/')
        return

    header()

    assets = [
        {'coin': 'BTC', 'quantity': 0.025, 'avg_price': 95000000, 'current_price': 98500000},
        {'coin': 'ETH', 'quantity': 0.7, 'avg_price': 3900000, 'current_price': 4200000},
        {'coin': 'XRP', 'quantity': 1200, 'avg_price': 780, 'current_price': 820},
    ]

    trades = [
        {'coin': 'BTC', 'type': '매수', 'method': '수동', 'price': 95000000, 'quantity': 0.01, 'date': '2026-05-13 14:20'},
        {'coin': 'ETH', 'type': '매수', 'method': '자동', 'price': 3900000, 'quantity': 0.5, 'date': '2026-05-12 18:10'},
        {'coin': 'XRP', 'type': '매도', 'method': '수동', 'price': 820, 'quantity': 300, 'date': '2026-05-10 09:30'},
    ]

    krw_balance = 7500000

    def format_won(value):
        return f'{value:,.0f}원'

    total_coin_value = sum(item['quantity'] * item['current_price'] for item in assets)
    total_buy_value = sum(item['quantity'] * item['avg_price'] for item in assets)
    total_asset = krw_balance + total_coin_value
    total_profit = total_coin_value - total_buy_value
    profit_rate = (total_profit / total_buy_value * 100) if total_buy_value > 0 else 0

    with ui.column().classes('w-full min-h-screen bg-[#F8FAFC] text-[#1E293B] p-8 gap-6'):
        with ui.column().classes('gap-1'):
            ui.label('포트폴리오').classes('text-4xl font-bold text-[#1E293B]')
            ui.label('보유 자산, 수익률, 거래 내역을 확인합니다.').classes('text-[#64748B]')

        with ui.row().classes('gap-4 w-full'):
            summary_cards = [
                ('총 평가금액', format_won(total_asset), '#2563EB'),
                ('총 손익', format_won(total_profit), '#2563EB' if total_profit >= 0 else '#EF4444'),
                ('수익률', f'{profit_rate:+.2f}%', '#2563EB' if profit_rate >= 0 else '#EF4444'),
                ('보유 원화', format_won(krw_balance), '#0F172A'),
            ]

            for title, value, color in summary_cards:
                with ui.card().classes('w-1/4 bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-5'):
                    ui.label(title).classes('text-sm text-[#64748B]')
                    ui.label(value).classes('text-2xl font-bold').style(f'color:{color};')

        with ui.row().classes('gap-6 w-full items-start'):
            with ui.card().classes('w-2/3 bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-6'):
                ui.label('보유 자산 현황').classes('text-2xl font-bold text-[#1E293B]')
                ui.label('코인별 수량, 평단가, 평가금액, 수익률입니다.').classes('text-[#64748B] text-sm mb-4')

                with ui.row().classes('w-full bg-[#EFF6FF] text-[#2563EB] rounded-lg px-4 py-3 font-bold'):
                    ui.label('코인').classes('w-1/5')
                    ui.label('보유 수량').classes('w-1/5')
                    ui.label('평균 매수가').classes('w-1/5')
                    ui.label('평가금액').classes('w-1/5')
                    ui.label('수익률').classes('w-1/5')

                for item in assets:
                    value = item['quantity'] * item['current_price']
                    buy_value = item['quantity'] * item['avg_price']
                    rate = ((value - buy_value) / buy_value * 100) if buy_value > 0 else 0
                    rate_color = '#2563EB' if rate >= 0 else '#EF4444'

                    with ui.row().classes('w-full items-center border-b border-[#E2E8F0] px-4 py-3'):
                        ui.label(item['coin']).classes('w-1/5 font-bold text-[#1E293B]')
                        ui.label(f"{item['quantity']:,.8f}".rstrip('0').rstrip('.')).classes('w-1/5 text-[#334155]')
                        ui.label(format_won(item['avg_price'])).classes('w-1/5 text-[#334155]')
                        ui.label(format_won(value)).classes('w-1/5 text-[#1E293B] font-semibold')
                        ui.label(f'{rate:+.2f}%').classes('w-1/5 font-bold').style(f'color:{rate_color};')

                ui.separator().classes('my-6 bg-[#E2E8F0]')

                with ui.row().classes('w-full items-center justify-between mb-4'):
                    with ui.column().classes('gap-1'):
                        ui.label('거래 내역').classes('text-2xl font-bold text-[#1E293B]')
                        ui.label('최근 매수·매도 기록입니다.').classes('text-[#64748B] text-sm')

                    trade_filter = ui.toggle(['전체', '매수', '매도'], value='전체').props('spread')

                trade_container = ui.column().classes('w-full gap-2')

                def render_trades():
                    trade_container.clear()

                    with trade_container:
                        filtered = trades
                        if trade_filter.value != '전체':
                            filtered = [item for item in trades if item['type'] == trade_filter.value]

                        if not filtered:
                            with ui.element('div').classes('w-full h-32 flex items-center justify-center bg-[#F1F5F9] rounded-xl border border-[#E2E8F0] text-[#64748B]'):
                                ui.label('해당 조건의 거래 내역이 없습니다.')
                            return

                        with ui.row().classes('w-full bg-[#EFF6FF] text-[#2563EB] rounded-lg px-4 py-3 font-bold'):
                            ui.label('코인').classes('w-1/6')
                            ui.label('유형').classes('w-1/6')
                            ui.label('방식').classes('w-1/6')
                            ui.label('체결가').classes('w-1/6')
                            ui.label('수량').classes('w-1/6')
                            ui.label('일시').classes('w-1/6')

                        for item in filtered:
                            type_color = '#2563EB' if item['type'] == '매수' else '#EF4444'
                            with ui.row().classes('w-full items-center border-b border-[#E2E8F0] px-4 py-3'):
                                ui.label(item['coin']).classes('w-1/6 font-bold')
                                ui.label(item['type']).classes('w-1/6 font-bold').style(f'color:{type_color};')
                                ui.label(item['method']).classes('w-1/6 text-[#334155]')
                                ui.label(format_won(item['price'])).classes('w-1/6 text-[#334155]')
                                ui.label(str(item['quantity'])).classes('w-1/6 text-[#334155]')
                                ui.label(item['date']).classes('w-1/6 text-[#64748B]')

                trade_filter.on('update:model-value', lambda _: render_trades())
                render_trades()

            with ui.card().classes('w-1/3 bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-6'):
                ui.label('자산 배분').classes('text-2xl font-bold text-[#1E293B]')
                ui.label('현재 보유 자산 비중입니다.').classes('text-[#64748B] text-sm mb-4')

                allocation = [('KRW', krw_balance)] + [(item['coin'], item['quantity'] * item['current_price']) for item in assets]

                for name, value in allocation:
                    percent = value / total_asset * 100 if total_asset > 0 else 0
                    ui.label(f'{name} {percent:.1f}%').classes('text-[#1E293B] font-bold mt-2')
                    ui.linear_progress(percent / 100).classes('w-full text-[#2563EB]')
                    ui.label(format_won(value)).classes('text-[#64748B] text-sm')

                ui.separator().classes('my-6 bg-[#E2E8F0]')

                ui.label('성과 리포트').classes('text-2xl font-bold text-[#1E293B]')
                ui.label('가장 많이 보유한 코인: BTC').classes('text-[#334155] mt-2')
                ui.label('가장 수익률이 높은 코인: ETH').classes('text-[#334155]')
                ui.label('최근 거래: XRP 매도').classes('text-[#334155]')

                def reset_portfolio():
                    ui.notify('모의투자 초기화는 백엔드 연동 후 적용 예정입니다.', type='warning')

                ui.button(
                    '모의투자 초기화',
                    on_click=reset_portfolio
                ).classes('w-full bg-[#EF4444] font-bold rounded-lg py-3 mt-6').style('color:#FFFFFF !important;')


@ui.page('/deposit')
def deposit_page():
    if not is_logged_in():
        ui.navigate.to('/')
        return

    header()

    def format_won(value):
        return f'{value:,.0f}원'

    def fmt_dt(iso_str):
        # "2026-06-03T16:03:56.4..." → "2026-06-03 16:03" (UTC 기준)
        if not iso_str:
            return ''
        return iso_str.replace('T', ' ')[:16]

    def tx_to_history(rows):
        # 백엔드 거래내역(DEPOSIT/WITHDRAW) → 화면 표시용(입금/출금)으로 변환
        result = []
        for item in rows:
            result.append({
                'type': '입금' if item.get('transaction_type') == 'DEPOSIT' else '출금',
                'amount': item.get('amount', 0),
                'balance_after': item.get('balance_after', 0),
                'date': fmt_dt(item.get('created_at')),
            })
        return result

    # 백엔드에서 잔고 + 입출금 내역 조회
    try:
        balance_data = api_client.get_balance(get_token())
        history = tx_to_history(api_client.get_transactions(get_token()))
    except ApiError as e:
        if e.status == 401:
            clear_session()
            ui.notify('세션이 만료되었습니다. 다시 로그인해주세요.', type='warning')
            ui.navigate.to('/')
            return
        # 연결 실패 등 → 오류 안내 + 다시 시도 버튼
        with ui.column().classes('w-full min-h-screen bg-[#F8FAFC] text-[#1E293B] p-8 gap-6'):
            with ui.card().classes('w-full bg-white border border-[#FECACA] rounded-2xl shadow-lg p-8'):
                ui.label('입출금 정보를 불러오지 못했습니다').classes('text-2xl font-bold text-[#EF4444]')
                ui.label(e.message).classes('text-[#64748B] mb-4')
                ui.button(
                    '다시 시도', on_click=lambda: ui.navigate.to('/deposit')
                ).classes('bg-[#2563EB] font-bold rounded-lg px-5 py-2').style('color:#FFFFFF !important;')
        return

    balance = {'krw': balance_data['krw_balance']}

    with ui.column().classes(
        'w-full min-h-screen bg-[#F8FAFC] text-[#1E293B] p-8 gap-6'
    ):
        # 제목 영역
        with ui.column().classes('gap-1'):
            ui.label('입출금').classes('text-4xl font-bold text-[#1E293B]')
            ui.label('가상 원화를 입금하거나 출금하고 내역을 확인합니다.').classes(
                'text-[#64748B]'
            )

        with ui.row().classes('gap-6 w-full items-start'):

            # 왼쪽: 잔고 + 입출금 폼
            with ui.card().classes(
                'w-1/3 bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-6'
            ):
                ui.label('보유 원화').classes('text-sm text-[#64748B]')
                balance_label = ui.label(format_won(balance['krw'])).classes(
                    'text-4xl font-bold mb-8 text-[#0F172A]'
                )

                mode = ui.toggle(
                    ['입금', '출금'],
                    value='입금'
                ).classes('mb-5').props('spread')

                amount_input = ui.input(
                    placeholder='금액 입력'
                ).props(
                    'outlined type=number'
                ).classes(
                    'w-full mb-3'
                ).style(
                    'background:#FFFFFF; border-radius:10px; color:#1E293B;'
                )

                preview_label = ui.label('처리 후 잔고: -').classes(
                    'text-[#64748B] text-sm mb-4'
                )

                def update_preview():
                    if not amount_input.value:
                        preview_label.text = '처리 후 잔고: -'
                        preview_label.classes(replace='text-[#64748B] text-sm mb-4')
                        return

                    try:
                        amount = int(amount_input.value)
                    except ValueError:
                        preview_label.text = '올바른 금액을 입력해주세요.'
                        preview_label.classes(replace='text-[#EF4444] text-sm mb-4')
                        return

                    if amount <= 0:
                        preview_label.text = '올바른 금액을 입력해주세요. (1원 이상)'
                        preview_label.classes(replace='text-[#EF4444] text-sm mb-4')
                        return

                    if mode.value == '입금':
                        after = balance['krw'] + amount
                    else:
                        after = balance['krw'] - amount

                    if after < 0:
                        preview_label.text = '출금 금액이 보유 잔고를 초과합니다.'
                        preview_label.classes(replace='text-[#EF4444] text-sm mb-4')
                    else:
                        preview_label.text = f'처리 후 잔고: {format_won(after)}'
                        preview_label.classes(replace='text-[#2563EB] text-sm mb-4')

                amount_input.on('update:model-value', lambda _: update_preview())

                quick_amounts = [
                    ('10만원', 100000),
                    ('50만원', 500000),
                    ('100만원', 1000000),
                    ('500만원', 5000000),
                    ('1000만원', 10000000),
                    ('초기화', 0),
                ]
                quick_amount_buttons = []

                def get_quick_amount_label(label, value):
                    if value == 0:
                        return label

                    sign = '+' if mode.value == '입금' else '-'
                    return f'{sign}{label}'

                def update_quick_amount_labels():
                    for button, label, value in quick_amount_buttons:
                        button.text = get_quick_amount_label(label, value)

                def handle_mode_change():
                    update_preview()
                    update_quick_amount_labels()

                mode.on('update:model-value', lambda _: handle_mode_change())

                with ui.grid(columns=3).classes('gap-2 w-full mb-5'):

                    def set_amount(value):
                        if value == 0:
                            amount_input.value = ''
                            update_preview()
                            return

                        try:
                            current_amount = int(amount_input.value) if amount_input.value else 0
                        except ValueError:
                            current_amount = 0

                        new_amount = current_amount + value
                        amount_input.value = str(new_amount)
                        update_preview()

                    for label, value in quick_amounts:
                        button = ui.button(
                            get_quick_amount_label(label, value),
                            on_click=lambda v=value: set_amount(v)
                        ).classes(
                            'bg-[#DBEAFE] border border-[#BFDBFE] rounded-lg font-bold'
                        ).style(
                            'color:#FFFFFF !important;'
                        )
                        quick_amount_buttons.append((button, label, value))

                def process_transaction():
                    if not amount_input.value:
                        ui.notify('금액을 입력해주세요.', type='warning')
                        return

                    try:
                        amount = int(amount_input.value)
                    except ValueError:
                        ui.notify('올바른 금액을 입력해주세요.', type='warning')
                        return

                    if amount <= 0:
                        ui.notify('올바른 금액을 입력해주세요. 1원 이상 입력해야 합니다.', type='warning')
                        return

                    # 클라이언트 1차 검증 (서버에서도 다시 검증한다)
                    if mode.value == '출금' and amount > balance['krw']:
                        ui.notify('출금 금액이 보유 잔고를 초과합니다.', type='negative')
                        return

                    # 백엔드 호출 (INSUFFICIENT_BALANCE 등 서버 오류는 그대로 표시)
                    try:
                        if mode.value == '입금':
                            result = api_client.deposit(get_token(), amount)
                            ui.notify('입금이 완료되었습니다.', type='positive')
                        else:
                            result = api_client.withdraw(get_token(), amount)
                            ui.notify('출금이 완료되었습니다.', type='positive')
                    except ApiError as e:
                        if e.status == 401:
                            clear_session()
                            ui.notify('세션이 만료되었습니다. 다시 로그인해주세요.', type='warning')
                            ui.navigate.to('/')
                            return
                        ui.notify(e.message, type='negative')
                        return

                    # 잔고 갱신 + 내역 재조회 (서버를 단일 진실 공급원으로 사용)
                    balance['krw'] = result['krw_balance']
                    try:
                        history[:] = tx_to_history(api_client.get_transactions(get_token()))
                    except ApiError:
                        # 내역 재조회 실패는 치명적이지 않음 → 직전 내역 유지
                        pass

                    balance_label.text = format_won(balance['krw'])
                    amount_input.value = ''
                    update_preview()
                    render_history()

                ui.button(
                    '확인',
                    on_click=process_transaction
                ).classes(
                    'w-full bg-[#2563EB] text-white font-bold rounded-lg py-3'
                )

            # 오른쪽: 입출금 내역
            with ui.card().classes(
                'w-2/3 bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-6'
            ):
                with ui.row().classes('w-full items-center justify-between mb-4'):
                    with ui.column().classes('gap-1'):
                        ui.label('입출금 내역').classes('text-2xl font-bold text-[#1E293B]')
                        ui.label('가상 원화 입금 및 출금 기록입니다.').classes(
                            'text-[#64748B] text-sm'
                        )

                    filter_type = ui.toggle(
                        ['전체', '입금', '출금'],
                        value='전체'
                    ).props('spread')

                history_container = ui.column().classes('w-full gap-2')

                def render_history():
                    history_container.clear()

                    with history_container:
                        filtered_history = history

                        if filter_type.value != '전체':
                            filtered_history = [
                                item for item in history
                                if item['type'] == filter_type.value
                            ]

                        if not filtered_history:
                            with ui.element('div').classes(
                                'w-full h-40 flex items-center justify-center bg-[#F1F5F9] rounded-xl border border-[#E2E8F0] text-[#64748B]'
                            ):
                                ui.label('해당 조건의 입출금 내역이 없습니다.')
                            return

                        with ui.row().classes(
                            'w-full bg-[#EFF6FF] text-[#2563EB] rounded-lg px-4 py-3 font-bold'
                        ):
                            ui.label('유형').classes('w-1/5')
                            ui.label('금액').classes('w-1/5')
                            ui.label('처리 후 잔고').classes('w-1/5')
                            ui.label('일시').classes('w-2/5')

                        for item in filtered_history:
                            type_color = '#2563EB' if item['type'] == '입금' else '#EF4444'

                            with ui.row().classes(
                                'w-full items-center border-b border-[#E2E8F0] px-4 py-3'
                            ):
                                ui.label(item['type']).classes(
                                    'w-1/5 font-bold'
                                ).style(
                                    f'color:{type_color};'
                                )

                                ui.label(format_won(item['amount'])).classes(
                                    'w-1/5 text-[#1E293B] font-semibold'
                                )
                                ui.label(format_won(item['balance_after'])).classes(
                                    'w-1/5 text-[#334155]'
                                )
                                ui.label(item['date']).classes(
                                    'w-2/5 text-[#64748B]'
                                )

                filter_type.on('update:model-value', lambda _: render_history())
                render_history()


@ui.page('/settings')
def settings_page():
    if not is_logged_in():
        ui.navigate.to('/')
        return

    header()

    with ui.column().classes('w-full min-h-screen bg-[#F8FAFC] text-[#1E293B] p-8 gap-6'):
        with ui.column().classes('gap-1'):
            ui.label('공통 설정').classes('text-4xl font-bold text-[#1E293B]')
            ui.label('API 키, 알림 설정, 회원 관리를 설정합니다.').classes('text-[#64748B]')

        with ui.row().classes('gap-6 w-full items-start'):

            with ui.card().classes('w-1/3 bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-6'):
                ui.label('API 키 설정').classes('text-2xl font-bold text-[#1E293B]')
                ui.label('Upbit API 키를 등록하고 연결 상태를 확인합니다.').classes('text-[#64748B] text-sm mb-4')

                access_key = ui.input(placeholder='Access Key').props('outlined autocomplete=off').classes('w-full mb-3').style('background:#FFFFFF; border-radius:10px; color:#1E293B;')
                secret_key = ui.input(placeholder='Secret Key', password=True, password_toggle_button=True).props('outlined autocomplete=new-password').classes('w-full mb-4').style('background:#FFFFFF; border-radius:10px; color:#1E293B;')

                api_status = ui.label('상태: 미등록').classes('text-[#64748B] text-sm mb-4')

                # 진입 시 등록 상태를 백엔드에서 조회 (등록돼 있으면 마스킹된 키 표시)
                try:
                    status_info = api_client.get_api_key_status(get_token())
                    if status_info.get('registered'):
                        masked = status_info.get('access_key_masked') or ''
                        api_status.text = f'상태: 등록됨 ({masked})'
                        api_status.classes(replace='text-[#2563EB] text-sm mb-4')
                except ApiError as e:
                    if e.status == 401:
                        clear_session()
                        ui.navigate.to('/')
                        return
                    # 그 외 오류는 화면을 막지 않고 미등록 상태로 표시

                def save_api_key():
                    if not access_key.value:
                        ui.notify('Access Key를 입력해주세요.', type='warning')
                        return
                    if not secret_key.value:
                        ui.notify('Secret Key를 입력해주세요.', type='warning')
                        return

                    try:
                        api_client.save_api_key(get_token(), access_key.value, secret_key.value)
                    except ApiError as e:
                        if e.status == 401:
                            clear_session()
                            ui.notify('세션이 만료되었습니다. 다시 로그인해주세요.', type='warning')
                            ui.navigate.to('/')
                            return
                        ui.notify(e.message, type='negative')
                        return

                    api_status.text = '상태: 저장 완료'
                    api_status.classes(replace='text-[#2563EB] text-sm mb-4')
                    ui.notify('API 키가 저장되었습니다.', type='positive')

                def test_api_connection():
                    # 실제 업비트 연결 검증은 데모 범위 밖이라 안내만 표시한다.
                    if not access_key.value or not secret_key.value:
                        ui.notify('API 키를 먼저 입력해주세요.', type='warning')
                        return
                    ui.notify('연결 테스트는 데모 범위에 포함되지 않았습니다. 저장만 동작합니다.', type='info')

                with ui.row().classes('gap-2 w-full'):
                    ui.button('저장', on_click=save_api_key).classes('bg-[#2563EB] font-bold rounded-lg px-5').style('color:#FFFFFF !important;')
                    ui.button('연결 테스트', on_click=test_api_connection).classes('bg-[#2563EB] border border-[#2563EB] font-bold rounded-lg px-5').style('color:#FFFFFF !important;')

            with ui.card().classes('w-1/3 bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-6'):
                ui.label('알림 설정').classes('text-2xl font-bold text-[#1E293B]')
                ui.label('자동매매 신호와 오류 알림을 설정합니다.').classes('text-[#64748B] text-sm mb-4')

                trade_signal = ui.switch('매매 신호 알림', value=True).classes('text-[#334155]')
                stop_loss = ui.switch('손절/익절 알림', value=True).classes('text-[#334155]')
                error_notice = ui.switch('오류 알림', value=True).classes('text-[#334155]')

                def save_notification():
                    ui.notify('알림 설정이 저장되었습니다.', type='positive')

                ui.separator().classes('my-4 bg-[#E2E8F0]')
                ui.button('알림 설정 저장', on_click=save_notification).classes('w-full bg-[#2563EB] font-bold rounded-lg py-3').style('color:#FFFFFF !important;')

                def show_notification_state():
                    ui.notify(f'매매 신호: {trade_signal.value}, 손절/익절: {stop_loss.value}, 오류: {error_notice.value}')

                ui.button('설정 상태 확인', on_click=show_notification_state).classes('w-full bg-[#2563EB] border border-[#2563EB] font-bold rounded-lg py-3 mt-3').style('color:#FFFFFF !important;')

            with ui.card().classes('w-1/3 bg-white text-[#1E293B] border border-[#E2E8F0] rounded-2xl shadow-lg p-6'):
                ui.label('회원 관리').classes('text-2xl font-bold text-[#1E293B]')
                ui.label('로그아웃 또는 회원 탈퇴를 진행합니다.').classes('text-[#64748B] text-sm mb-4')

                ui.label('로그인 계정').classes('text-sm text-[#64748B]')
                ui.label(current_email()).classes('text-lg font-bold text-[#1E293B] mb-4')

                ui.button('로그아웃', on_click=do_logout).classes('w-full bg-[#2563EB] border border-[#2563EB] font-bold rounded-lg py-3 mb-4').style('color:#FFFFFF !important;')

                ui.separator().classes('my-4 bg-[#E2E8F0]')
                ui.label('회원 탈퇴').classes('text-[#EF4444] font-bold')
                ui.label('회원 탈퇴 시 계정 이용이 제한됩니다.').classes('text-[#64748B] text-sm mb-4')

                def open_delete_dialog():
                    with ui.dialog() as dialog, ui.card().classes('bg-white text-[#222222] rounded-xl p-6 w-[420px]'):
                        ui.label('정말 탈퇴하시겠습니까?').classes('text-xl font-bold mb-2')
                        ui.label('탈퇴 시 로그인이 제한되며 서비스 이용이 불가합니다.').classes('text-[#666666] mb-6')

                        with ui.row().classes('w-full justify-end gap-2'):
                            ui.button('취소', on_click=dialog.close).classes('bg-white border border-[#D1D5DB] font-bold').style('color:#666666 !important;')

                            def delete_account():
                                # 회원 탈퇴는 데모 범위 밖(백엔드 삭제 엔드포인트 없음) → 안내만 표시
                                dialog.close()
                                ui.notify('회원 탈퇴 기능은 데모 범위에 포함되지 않았습니다.', type='warning')

                            ui.button('탈퇴', on_click=delete_account).classes('bg-[#EF4444] font-bold').style('color:#FFFFFF !important;')
                    dialog.open()

                ui.button('회원 탈퇴', on_click=open_delete_dialog).classes('w-full bg-[#EF4444] font-bold rounded-lg py-3').style('color:#FFFFFF !important;')


# app.storage.user 사용을 위해 storage_secret 이 반드시 필요하다.
# (운영 배포 시에는 환경변수 STORAGE_SECRET 로 충분히 긴 임의 값을 주입할 것)
STORAGE_SECRET = os.environ.get('STORAGE_SECRET', 'CHANGE_ME_dev_storage_secret_please_override')

ui.run(
    title='암호화폐 모의투자 시뮬레이션',
    port=int(os.environ.get('FRONTEND_PORT', '8080')),
    storage_secret=STORAGE_SECRET,
    reload=False,
)
