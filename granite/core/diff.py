from typing import List, Tuple, Optional
        result: List[Tuple[FileDiff, List[DiffHunk]]] = []
        current_file: Optional[FileDiff] = None
        current_hunks: List[DiffHunk] = []
        current_hunk: Optional[DiffHunk] = None