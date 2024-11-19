"""
SQLAlchemy models for Selfspy
"""

import zlib
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import (
    Index, Column, Boolean, Integer, String, DateTime, Binary, ForeignKey,
    create_engine
)
from sqlalchemy.orm import sessionmaker, relationship, backref

Base = declarative_base()

def initialize(fname: str) -> sessionmaker:
    """Initialize the database"""
    engine = create_engine(f'sqlite:///{fname}')
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)

class SpookMixin:
    """Base mixin for all models"""
    
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.now, index=True)

class Process(SpookMixin, Base):
    """Model for storing process information"""
    name = Column(String, index=True, unique=True)

    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return f"<Process '{self.name}'>"

class Window(SpookMixin, Base):
    """Model for storing window information"""
    title = Column(String, index=True)
    process_id = Column(Integer, ForeignKey('process.id'), nullable=False, index=True)
    
    process = relationship("Process", backref=backref('windows'))

    def __init__(self, title: str, process_id: int):
        self.title = title
        self.process_id = process_id

    def __repr__(self) -> str:
        return f"<Window '{self.title}'>"

class Keys(SpookMixin, Base):
    """Model for storing keystroke information"""
    text = Column(Binary, nullable=False)
    process_id = Column(Integer, ForeignKey('process.id'), nullable=False, index=True)
    window_id = Column(Integer, ForeignKey('window.id'), nullable=False)
    nrkeys = Column(Integer, index=True)
    
    process = relationship("Process", backref=backref('keys'))
    window = relationship("Window", backref=backref('keys'))

    def __init__(self, text: bytes, nrkeys: int, process_id: int, window_id: int):
        self.text = text
        self.nrkeys = nrkeys
        self.process_id = process_id
        self.window_id = window_id

    def decrypt_text(self, cipher=None) -> str:
        """Decrypt the stored text"""
        if cipher:
            try:
                decrypted = cipher.decrypt(self.text)
                return decrypted.rstrip(b'\0').decode('utf-8')
            except:
                return ''
        return self.text.decode('utf-8')

class Click(SpookMixin, Base):
    """Model for storing mouse click information"""
    button = Column(Integer, nullable=False)
    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False)
    nrmoves = Column(Integer, nullable=False, default=0)
    
    process_id = Column(Integer, ForeignKey('process.id'), nullable=False, index=True)
    window_id = Column(Integer, ForeignKey('window.id'), nullable=False)
    
    process = relationship("Process", backref=backref('clicks'))
    window = relationship("Window", backref=backref('clicks'))

    def __init__(self, button: int, x: int, y: int, process_id: int, window_id: int):
        self.button = button
        self.x = x
        self.y = y
        self.nrmoves = 0
        self.process_id = process_id
        self.window_id = window_id

    def __repr__(self) -> str:
        return f"<Click ({self.x}, {self.y}), button={self.button}>"
    