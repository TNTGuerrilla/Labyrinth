from collections import deque


def bfs_path(grid, start, end):
    parent = {start: None}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        if cell == end:
            break
        for n in grid.open_neighbors(cell):
            if n not in parent:
                parent[n] = cell
                queue.append(n)
    path = [end]
    while parent[path[-1]] is not None:
        path.append(parent[path[-1]])
    return path[::-1]


def assert_perfect(grid):
    """Spanning tree check: n-1 passages and everything reachable means no loops."""
    total = grid.cols * grid.rows
    assert grid.passage_count() == total - 1
    seen = {(0, 0)}
    queue = deque([(0, 0)])
    while queue:
        cell = queue.popleft()
        for n in grid.open_neighbors(cell):
            if n not in seen:
                seen.add(n)
                queue.append(n)
    assert len(seen) == total
