"""Exercise the actual Kodi adapter methods without a Kodi runtime."""
import ast
from pathlib import Path
from types import SimpleNamespace

from arc import titlepage


def adapter():
    source = Path(__file__).parents[1] / 'resources/lib/kodi/windows/details.py'
    tree = ast.parse(source.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'DetailsWindow')
    names = {'_load_seasons', '_show_seasons', '_season_menu', '_card_menu'}
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
    tree.body = [ast.ClassDef(name='Adapter', bases=[], keywords=[], body=methods, decorator_list=[])]
    ns = {'titlepage': titlepage, 'T': lambda n: n, 'SEASONS': 200, 'EPISODES': 201,
          'toast': SimpleNamespace(show=lambda _: None), 'menu': SimpleNamespace(choose=lambda *a: 0)}
    exec(compile(ast.fix_missing_locations(tree), str(source), 'exec'), ns)
    obj = ns['Adapter']()
    obj.show_missing = False
    obj._seasons_request = 0
    obj.item_id = 'show'
    return obj, ns


def test_toggle_commits_only_successful_latest_response():
    w, ns = adapter()
    requests, applied, errors = [], [], []
    w.run_async = lambda work, done: requests.append((work, done))
    w.session = SimpleNamespace(api=SimpleNamespace(seasons=lambda id, missing: (id, missing)))
    w._show_seasons = lambda data, error: applied.append(data)
    ns['toast'].show = errors.append
    w._load_seasons(True)
    assert requests[0][0]() == ('show', True)
    assert not w.show_missing
    w._load_seasons(False)
    requests[0][1]({'seasons': ['stale']}, None)
    assert not applied
    requests[1][1]({'seasons': []}, None)
    assert applied == [{'seasons': []}] and not w.show_missing
    w._load_seasons(True)
    requests[2][1](None, RuntimeError('offline'))
    assert not w.show_missing and errors == [30004]
    w._load_seasons(True)
    requests[3][1]({'seasons': []}, None)
    assert w.show_missing


def test_visibility_toggle_remains_reachable_without_files():
    w, ns = adapter()
    w.tabs = [{'season_number': 2, 'episodes': [{'available': False}]}]
    w.season_index = 0
    w.list_control = lambda _: SimpleNamespace(getSelectedPosition=lambda: 0)
    w._tab_name = lambda _: 'Season 2'
    requested, menus = [], []
    w._load_seasons = lambda show_missing: requested.append(show_missing)
    ns['menu'].choose = lambda title, options: menus.append(options) or 0
    assert w._season_menu()
    assert menus == [[30600]] and requested == [True]
    w.show_missing = True
    w.tabs = [{'unplaced': True, 'episodes': [{'id': 'disk'}]}]
    assert w._season_menu()
    assert menus[-1] == [30601] and requested[-1] is False


def test_missing_episode_has_no_mutating_context_menu():
    w, _ = adapter()
    w.getFocusId = lambda: 201
    w.list_control = lambda _: SimpleNamespace(getSelectedPosition=lambda: 0)
    w._tab_episodes = lambda: [{'available': False}]
    w.nav = lambda *a: (_ for _ in ()).throw(AssertionError('missing episode context opened'))
    assert w._card_menu() is False


def test_missing_entries_never_enter_play_or_watched_actions():
    missing = {'available': False, 'episode_number': 1}
    disk = {'id': 'disk', 'episode_number': 2, 'user_data': {'played': True}}
    tab = {'season_number': 1, 'episodes': [missing, disk]}
    assert titlepage.next_to_play([tab]) is disk
    assert titlepage.season_episode_ids(tab) == ['disk']
    assert titlepage.season_actions(tab) == ['unwatched']
    assert titlepage.mark_season(tab, True)[0] == missing


def test_toggle_preserves_season_when_missing_seasons_are_inserted():
    w, _ = adapter()
    w.tabs = [{'season_number': 2, 'episodes': [{'id': 'disk'}]}]
    w.season_index = 0
    w.focus_episode = None
    w.item = None
    w.action = None
    w._tab_name = lambda tab: str(tab['season_number'])
    w._tab_episodes = lambda: w.tabs[w.season_index]['episodes']
    w.getFocusId = lambda: 200
    selected = []
    w.list_control = lambda _: SimpleNamespace(getSelectedPosition=lambda: 0, reset=lambda: None,
                                               addItem=lambda _: None, selectItem=selected.append)
    w._show_episodes = lambda index, episode_id=None: selected.append((index, episode_id))
    w.focus_when_visible = lambda control: selected.append(('focus', control))
    w._show_seasons.__func__.__globals__['list_item'] = lambda *a, **kw: None
    w._show_seasons({'seasons': [{'season_number': 1, 'episodes': [{'available': False}]},
                               {'season_number': 2, 'episodes': [{'id': 'disk'}]}]}, None)
    assert selected == [1, (1, 'disk'), ('focus', 200)]
