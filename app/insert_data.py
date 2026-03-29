import json
from pathlib import Path
from sqlmodel import SQLModel, Session
from .models import User, Novel, Chapter, Episode
from .database import engine

def init_data(path: str):
    path_obj = Path(path)
    if not path_obj.exists():
        print(f"File not found: {path}")
        return
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    with Session(engine) as session:
        author = User(name=data["author"])
        session.add(author)
        session.flush()

        novel = Novel(
            title=data["title"],
            author=author
        )

        for ch_data in data["chapters"]:
            chapter = Chapter(
                title=ch_data["title"],
                order=ch_data["order"],
                novel=novel
            )
            
            for ep_data in ch_data["episodes"]:
                episode = Episode(
                    title=ep_data["title"],
                    content=ep_data["content"],
                    chapter=chapter
                )
                chapter.episodes.append(episode)
            
            novel.chapters.append(chapter)
        
        session.add(novel)
        session.commit()
        print(f"Successfully initialized data: {novel.title}")