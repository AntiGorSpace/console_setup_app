import os

from classes.Pager import Pager, Page
from classes.SQLite import SQLite


if __name__=='__main__':
    main_path = os.path.dirname(os.path.realpath(__file__))
    base = SQLite(main_path)

    from pages.wg import WGPage

    class MainPage(Page):
        def before_add(self):
            self.options = {
                'w': {'name': 'WireGuard', 'page':WGPage()},
            }

    pager = Pager()
    pager.next_page(MainPage())
