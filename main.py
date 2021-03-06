import asyncio
import curses
import random
import time
from itertools import cycle
from obstacles import Obstacle, show_obstacles, has_collision
from curses_tools import draw_frame, get_frame_size, read_controls
from physics import update_speed
from explosion import explode


TIC_TIMEOUT = 0.0005
MIN_ROW = 10
MIN_COL = 20
BORDER = 1
STARS_CNT = 20
ROCKET_FRAMES = [
    'frames/rocket_frame_1.txt', 
    'frames/rocket_frame_2.txt'
]
GARBAGE_FRAMES = [
    'frames/duck.txt', 
    'frames/hubble.txt',
    'frames/lamp.txt',
    'frames/trash_large.txt',
    'frames/trash_small.txt',
    'frames/trash_xl.txt'
]
GAME_OVER='frames/game_over.txt'
COROUTINES = []
OBSTACLES = []
OBSTACLES_IN_LAST_COLLISIONS = []
YEAR = 1957
PHRASES = {
    1957: "First Sputnik",
    1961: "Gagarin flew!",
    1969: "Armstrong got on the moon!",
    1971: "First orbital space station Salute-1",
    1981: "Flight of the Shuttle Columbia",
    1998: 'ISS start building',
    2011: 'Messenger launch to Mercury',
    2020: "Take the plasma gun! Shoot the garbage!",
}


def get_garbage_delay_tics(year):
    if year < 1961:
        return None
    elif year < 1969:
        return 20 * 2
    elif year < 1981:
        return 14 * 2
    elif year < 1995:
        return 10 * 2
    elif year < 2010:
        return 8 * 2
    elif year < 2020:
        return 6 * 2
    else:
        return 2 * 2


async def increment_year():
    tics_in_one_year = 50
    while True:
        await sleep(tics_in_one_year)
        global YEAR
        YEAR += 1


def get_frame(filepath):
    with open(filepath, "r") as file:
        return file.read()
     

async def sleep(tics=1):
    if tics != 0:
        for _ in range(tics):
            await asyncio.sleep(0)
    else:
        await asyncio.sleep(0)


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """
    Animate garbage, flying from top to bottom. 
    Column position will stay same, as specified on start.
    """

    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row_size, column_size = get_frame_size(garbage_frame)

    row = 0
    obstacle = Obstacle(
            row, column, row_size, column_size
    )
    OBSTACLES.append(
        obstacle
    )
    
    while row < rows_number:
        if obstacle in OBSTACLES_IN_LAST_COLLISIONS:
            OBSTACLES.remove(obstacle)
            OBSTACLES_IN_LAST_COLLISIONS.remove(obstacle)
            return

        obstacle.column = column
        obstacle.row = row
        draw_frame(canvas, row, column, garbage_frame)
        await sleep(2)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed
    else:
        OBSTACLES.remove(obstacle)


async def fire(
    canvas,
    start_row,
    start_column,
    rows_speed=-0.3,
    columns_speed=0
):
    """
    Display animation of gun shot, direction and speed can be specified.
    """

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()
    
    while 0 < row < max_row and 0 < column < max_column:
        for obstacle in OBSTACLES:
            if obstacle.has_collision(
                row, column
            ):
                await explode(canvas, row, column)
                OBSTACLES_IN_LAST_COLLISIONS.append(obstacle)
                return
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def show_gameover(canvas):
    gameover_frame = get_frame(GAME_OVER)
    row_size, column_size = get_frame_size(gameover_frame)
    while True:
        draw_frame(
            canvas,
            canvas.getmaxyx()[0]/2 - row_size/2,
            canvas.getmaxyx()[1]/2 - column_size/2,
            gameover_frame
        )
        await asyncio.sleep(0)


async def run_spaceship(canvas, row, column, frames):
    """
    Rocket flame coroutine.
    Fire coroutine.
    Rocket control coroutine with speed processing.
    """
    row_size, col_size = get_frame_size(frames[0])
    max_row, max_col = canvas.getmaxyx()
    row_speed, column_speed = 0, 0
    while True:
        for item in cycle(frames):
            rows_direction, columns_direction, space = read_controls(canvas)

            row_speed, column_speed = update_speed(
                row_speed=row_speed,
                column_speed=column_speed,
                rows_direction=rows_direction,
                columns_direction=columns_direction,
                row_speed_limit=5,
                column_speed_limit=5
            )

            new_row = row + rows_direction + row_speed
            new_column = column + columns_direction + column_speed

            if BORDER <= new_row <= max_row - row_size - BORDER:
                row = new_row
            if new_row >= max_row - row_size - BORDER:
                row = max_row - row_size - BORDER
            if new_row <= BORDER:
                row = BORDER

            if BORDER <= new_column <= max_col - col_size - BORDER:
                column = new_column
            if new_column >= max_col - col_size - BORDER:
                column = max_col - col_size - BORDER
            if new_column <= BORDER:
                column = BORDER

            # shooting animation coroutine
            if YEAR >= 2020 and space:
                COROUTINES.append(
                    fire(
                        canvas,
                        start_row=row, 
                        start_column=column,
                    )
                )
            draw_frame(canvas, row, column, item)
            for obstacle in OBSTACLES:
                if obstacle.has_collision(
                    row, column
                ):
                    canvas.refresh()
                    await show_gameover(canvas)
                    
            await sleep(5)
            draw_frame(
                canvas, row, column, item, negative=True
            )


async def blink(canvas, row, column, symbol):
    """
    Star blinking coroutine.
    """
    star_freq = 5
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        await sleep(5 * star_freq)
        canvas.addstr(row, column, symbol, curses.A_NORMAL)
        await sleep(1 * star_freq)
        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await sleep(3 * star_freq)
        canvas.addstr(row, column, symbol)
        await sleep(1 * star_freq)


async def fill_orbit_with_garbage(canvas):
    """
    Generate garbage coroutines.
    """
    while True:
        delay = get_garbage_delay_tics(YEAR)
        if delay:
            random_frame = GARBAGE_FRAMES[
                random.randint(
                    a=0,
                    b=len(GARBAGE_FRAMES) - 1
                )
            ]
            COROUTINES.append(
                fly_garbage(
                    canvas,
                    column=random.randint(
                        a=0,
                        b=canvas.getmaxyx()[1] - 1
                    ),
                    garbage_frame=get_frame(random_frame)
                )
            )
            await sleep(delay) 
        else:
            await asyncio.sleep(0)


async def show_year(canvas):
    rows_number, columns_number = canvas.getmaxyx()
    offset = 2
    while True:
        try:
            text = f'{YEAR}: {PHRASES[YEAR]}'
        except KeyError:
            text = str(YEAR)
        draw_frame(canvas, offset, columns_number - len(text) - offset, text)
        await asyncio.sleep(0)
        draw_frame(canvas, offset, columns_number - len(text) - offset, text, negative=True)


def draw(canvas):
    """
    Handmade event-loop.
    """
    curses.curs_set(False)
    canvas.nodelay(True)
    
    # stars coroutines
    for i in range(STARS_CNT):
        COROUTINES.append(
            blink(
                canvas, 
                random.randint(
                    0,
                    canvas.getmaxyx()[0] - 1
                ),
                random.randint(
                    0,
                    canvas.getmaxyx()[1] - 1
                ),
                random.choice('+*.:')
            )
        )
    
    # garbage generating coroutine
    COROUTINES.append(fill_orbit_with_garbage(canvas))
    
    # rocket processing coroutine
    COROUTINES.append(
        run_spaceship(
            canvas, 
            canvas.getmaxyx()[0]/2, 
            canvas.getmaxyx()[1]/2, 
            [get_frame(x) for x in ROCKET_FRAMES]
        )
    )

    COROUTINES.append(show_year(canvas))
    COROUTINES.append(increment_year())

    while True:
        for coroutine in COROUTINES.copy():
            canvas.border()
            if not COROUTINES:
                break
            try:
                coroutine.send(None)
            except StopIteration:
                COROUTINES.remove(coroutine)
            canvas.refresh()
            time.sleep(TIC_TIMEOUT)


def main():
    curses.update_lines_cols()
    curses.wrapper(draw)


if __name__ == '__main__':
    main()
