#!/usr/bin/env python
"""
    Modern GUI widgets for pandastable.
    
    This module provides enhanced tkinter widgets with:
    - Hover effects
    - Modern styling
    - Improved visual feedback
    - Better accessibility
    
    Created 2024
    Copyright (C) Damien Farrell

    This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 3
    of the License, or (at your option) any later version.
"""

from __future__ import absolute_import, division, print_function

try:
    from tkinter import *
    from tkinter.ttk import *
    from tkinter import font as tkfont
except:
    from Tkinter import *
    from ttk import *
    import tkFont as tkfont

from .gui_themes import COLORS, get_contrast_color, lighten_color, darken_color


class ModernButton(Button):
    """
    A modern styled button with hover effects.
    
    Features:
    - Smooth hover color transitions
    - Rounded appearance (via ttk styling)
    - Consistent padding
    """
    
    def __init__(self, parent, text='', command=None, style='primary', **kwargs):
        """
        Initialize ModernButton.
        
        Args:
            parent: Parent widget.
            text (str): Button text.
            command: Button command callback.
            style (str): Button style - 'primary', 'secondary', 'success', 'danger'.
            **kwargs: Additional ttk Button arguments.
        """
        self.button_style = style
        self._setup_style(parent)
        
        super().__init__(
            parent, 
            text=text, 
            command=command,
            style=f'Modern.{style.capitalize()}.TButton',
            **kwargs
        )
        
    def _setup_style(self, parent):
        """Set up the button style."""
        style = Style(parent)
        
        styles = {
            'primary': {
                'bg': COLORS['primary'],
                'fg': COLORS['white'],
                'hover': COLORS['primary_hover'],
            },
            'secondary': {
                'bg': COLORS['secondary'],
                'fg': COLORS['white'],
                'hover': COLORS['secondary_hover'],
            },
            'success': {
                'bg': COLORS['success'],
                'fg': COLORS['white'],
                'hover': darken_color(COLORS['success'], 0.1),
            },
            'danger': {
                'bg': COLORS['error'],
                'fg': COLORS['white'],
                'hover': darken_color(COLORS['error'], 0.1),
            },
        }
        
        if self.button_style in styles:
            s = styles[self.button_style]
            style_name = f'Modern.{self.button_style.capitalize()}.TButton'
            style.configure(
                style_name,
                padding=(12, 6),
                font=('Segoe UI', 9),
            )


class ModernEntry(Entry):
    """
    A modern styled entry widget with placeholder support.
    
    Features:
    - Placeholder text
    - Focus highlighting
    - Rounded borders (via styling)
    """
    
    def __init__(self, parent, placeholder='', **kwargs):
        """
        Initialize ModernEntry.
        
        Args:
            parent: Parent widget.
            placeholder (str): Placeholder text shown when empty.
            **kwargs: Additional ttk Entry arguments.
        """
        super().__init__(parent, **kwargs)
        
        self.placeholder = placeholder
        self.placeholder_color = COLORS['gray_400']
        self.default_fg = COLORS['gray_800']
        self._has_placeholder = False
        
        if placeholder:
            self._show_placeholder()
            self.bind('<FocusIn>', self._on_focus_in)
            self.bind('<FocusOut>', self._on_focus_out)
            
    def _show_placeholder(self):
        """Show placeholder text."""
        if not self.get():
            self._has_placeholder = True
            self.insert(0, self.placeholder)
            self.configure(foreground=self.placeholder_color)
            
    def _hide_placeholder(self):
        """Hide placeholder text."""
        if self._has_placeholder:
            self._has_placeholder = False
            self.delete(0, END)
            self.configure(foreground=self.default_fg)
            
    def _on_focus_in(self, event):
        """Handle focus in event."""
        self._hide_placeholder()
        
    def _on_focus_out(self, event):
        """Handle focus out event."""
        if not self.get():
            self._show_placeholder()
            
    def get(self):
        """Get entry value, excluding placeholder."""
        if self._has_placeholder:
            return ''
        return super().get()


class ModernFrame(Frame):
    """
    A modern styled frame with optional border and shadow effect.
    """
    
    def __init__(self, parent, border=False, padding=10, **kwargs):
        """
        Initialize ModernFrame.
        
        Args:
            parent: Parent widget.
            border (bool): Whether to show a border.
            padding (int): Internal padding.
            **kwargs: Additional ttk Frame arguments.
        """
        style = Style(parent)
        
        if border:
            style.configure('Modern.Border.TFrame', 
                          borderwidth=1, 
                          relief='solid')
            kwargs['style'] = 'Modern.Border.TFrame'
            
        super().__init__(parent, padding=padding, **kwargs)


class ModernLabelFrame(LabelFrame):
    """
    A modern styled label frame with improved typography.
    """
    
    def __init__(self, parent, text='', padding=10, **kwargs):
        """
        Initialize ModernLabelFrame.
        
        Args:
            parent: Parent widget.
            text (str): Frame label text.
            padding (int): Internal padding.
            **kwargs: Additional ttk LabelFrame arguments.
        """
        style = Style(parent)
        style.configure('Modern.TLabelframe', padding=padding)
        style.configure('Modern.TLabelframe.Label', 
                       font=('Segoe UI', 10, 'bold'),
                       foreground=COLORS['gray_700'])
        
        super().__init__(parent, text=text, style='Modern.TLabelframe', **kwargs)


class ModernNotebook(Notebook):
    """
    A modern styled notebook with improved tab appearance.
    """
    
    def __init__(self, parent, **kwargs):
        """
        Initialize ModernNotebook.
        
        Args:
            parent: Parent widget.
            **kwargs: Additional ttk Notebook arguments.
        """
        style = Style(parent)
        style.configure('Modern.TNotebook', tabmargins=(2, 5, 2, 0))
        style.configure('Modern.TNotebook.Tab',
                       padding=(16, 8),
                       font=('Segoe UI', 9))
        
        super().__init__(parent, style='Modern.TNotebook', **kwargs)


class ModernTreeview(Treeview):
    """
    A modern styled treeview with improved row appearance.
    """
    
    def __init__(self, parent, **kwargs):
        """
        Initialize ModernTreeview.
        
        Args:
            parent: Parent widget.
            **kwargs: Additional ttk Treeview arguments.
        """
        style = Style(parent)
        style.configure('Modern.Treeview',
                       font=('Segoe UI', 9),
                       rowheight=28)
        style.configure('Modern.Treeview.Heading',
                       font=('Segoe UI', 9, 'bold'),
                       padding=(8, 6))
        style.map('Modern.Treeview',
                 background=[('selected', COLORS['primary_light'])],
                 foreground=[('selected', COLORS['gray_800'])])
        
        super().__init__(parent, style='Modern.Treeview', **kwargs)


class ModernScale(Scale):
    """
    A modern styled scale/slider widget.
    """
    
    def __init__(self, parent, **kwargs):
        """
        Initialize ModernScale.
        
        Args:
            parent: Parent widget.
            **kwargs: Additional tk Scale arguments.
        """
        defaults = {
            'troughcolor': COLORS['gray_200'],
            'activebackground': COLORS['primary'],
            'highlightthickness': 0,
            'sliderrelief': 'flat',
            'font': ('Segoe UI', 9),
        }
        defaults.update(kwargs)
        super().__init__(parent, **defaults)


class ModernProgressbar(Progressbar):
    """
    A modern styled progress bar.
    """
    
    def __init__(self, parent, **kwargs):
        """
        Initialize ModernProgressbar.
        
        Args:
            parent: Parent widget.
            **kwargs: Additional ttk Progressbar arguments.
        """
        style = Style(parent)
        style.configure('Modern.Horizontal.TProgressbar',
                       troughcolor=COLORS['gray_200'],
                       background=COLORS['primary'],
                       thickness=8)
        
        super().__init__(parent, style='Modern.Horizontal.TProgressbar', **kwargs)


class HoverButton(Button):
    """
    A button with hover color change effect.
    
    Works with standard tkinter Button for full color control.
    """
    
    def __init__(self, parent, bg=None, hover_bg=None, **kwargs):
        """
        Initialize HoverButton.
        
        Args:
            parent: Parent widget.
            bg (str): Normal background color.
            hover_bg (str): Hover background color.
            **kwargs: Additional Button arguments.
        """
        super().__init__(parent, **kwargs)
        
        self.normal_bg = bg or COLORS['gray_100']
        self.hover_bg = hover_bg or COLORS['gray_200']
        
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        
    def _on_enter(self, event):
        """Handle mouse enter."""
        try:
            self.configure(background=self.hover_bg)
        except:
            pass
            
    def _on_leave(self, event):
        """Handle mouse leave."""
        try:
            self.configure(background=self.normal_bg)
        except:
            pass


class IconButton(Button):
    """
    A button designed for icon display with optional text.
    """
    
    def __init__(self, parent, image=None, text='', tooltip='', **kwargs):
        """
        Initialize IconButton.
        
        Args:
            parent: Parent widget.
            image: PhotoImage for the icon.
            text (str): Optional button text.
            tooltip (str): Tooltip text.
            **kwargs: Additional Button arguments.
        """
        defaults = {
            'compound': 'left' if text else 'image',
            'padding': (8, 4),
        }
        defaults.update(kwargs)
        
        super().__init__(parent, image=image, text=text, **defaults)
        
        if image:
            self.image = image  # Keep reference
            
        if tooltip:
            self._create_tooltip(tooltip)
            
    def _create_tooltip(self, text):
        """Create a tooltip for the button."""
        from .dialogs import ToolTip
        try:
            ToolTip.createToolTip(self, text)
        except:
            pass


class SearchEntry(Frame):
    """
    A search entry with icon and clear button.
    """
    
    def __init__(self, parent, placeholder='Search...', command=None, **kwargs):
        """
        Initialize SearchEntry.
        
        Args:
            parent: Parent widget.
            placeholder (str): Placeholder text.
            command: Callback when search text changes.
            **kwargs: Additional Frame arguments.
        """
        super().__init__(parent, **kwargs)
        
        self.command = command
        
        # Search icon label (using text as placeholder for actual icon)
        self.icon_label = Label(self, text='🔍', font=('Segoe UI', 10))
        self.icon_label.pack(side=LEFT, padx=(8, 4))
        
        # Entry
        self.entry = ModernEntry(self, placeholder=placeholder)
        self.entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 4))
        
        # Clear button
        self.clear_btn = Label(self, text='✕', font=('Segoe UI', 10), 
                              cursor='hand2')
        self.clear_btn.pack(side=RIGHT, padx=(0, 8))
        self.clear_btn.bind('<Button-1>', self._clear)
        
        # Bind entry changes
        self.entry.bind('<KeyRelease>', self._on_change)
        
    def _on_change(self, event):
        """Handle entry text change."""
        if self.command:
            self.command(self.get())
            
    def _clear(self, event=None):
        """Clear the search entry."""
        self.entry.delete(0, END)
        if self.command:
            self.command('')
            
    def get(self):
        """Get the search text."""
        return self.entry.get()
        
    def set(self, value):
        """Set the search text."""
        self.entry.delete(0, END)
        self.entry.insert(0, value)


class StatusLabel(Label):
    """
    A label for status messages with different severity styles.
    """
    
    STYLES = {
        'info': {'bg': COLORS['primary_light'], 'fg': COLORS['primary']},
        'success': {'bg': COLORS['success_light'], 'fg': COLORS['success']},
        'warning': {'bg': COLORS['warning_light'], 'fg': COLORS['warning']},
        'error': {'bg': COLORS['error_light'], 'fg': COLORS['error']},
    }
    
    def __init__(self, parent, text='', severity='info', **kwargs):
        """
        Initialize StatusLabel.
        
        Args:
            parent: Parent widget.
            text (str): Status message.
            severity (str): 'info', 'success', 'warning', or 'error'.
            **kwargs: Additional Label arguments.
        """
        style = Style(parent)
        style_name = f'Status.{severity.capitalize()}.TLabel'
        
        colors = self.STYLES.get(severity, self.STYLES['info'])
        style.configure(style_name,
                       background=colors['bg'],
                       foreground=colors['fg'],
                       padding=(12, 6),
                       font=('Segoe UI', 9))
        
        super().__init__(parent, text=text, style=style_name, **kwargs)
        
    def set_severity(self, severity):
        """Change the severity style."""
        style_name = f'Status.{severity.capitalize()}.TLabel'
        self.configure(style=style_name)


class CollapsibleFrame(Frame):
    """
    A frame that can be collapsed/expanded with a toggle button.
    """
    
    def __init__(self, parent, text='', collapsed=False, **kwargs):
        """
        Initialize CollapsibleFrame.
        
        Args:
            parent: Parent widget.
            text (str): Header text.
            collapsed (bool): Initial collapsed state.
            **kwargs: Additional Frame arguments.
        """
        super().__init__(parent, **kwargs)
        
        self._collapsed = collapsed
        
        # Header frame
        self.header = Frame(self)
        self.header.pack(fill=X)
        
        # Toggle button
        self.toggle_btn = Label(self.header, text='▼' if not collapsed else '▶',
                               font=('Segoe UI', 10), cursor='hand2')
        self.toggle_btn.pack(side=LEFT, padx=(4, 8))
        self.toggle_btn.bind('<Button-1>', self._toggle)
        
        # Title
        self.title = Label(self.header, text=text, 
                          font=('Segoe UI', 10, 'bold'))
        self.title.pack(side=LEFT)
        self.title.bind('<Button-1>', self._toggle)
        
        # Content frame
        self.content = Frame(self)
        if not collapsed:
            self.content.pack(fill=BOTH, expand=True, pady=(8, 0))
            
    def _toggle(self, event=None):
        """Toggle collapsed state."""
        self._collapsed = not self._collapsed
        
        if self._collapsed:
            self.content.pack_forget()
            self.toggle_btn.configure(text='▶')
        else:
            self.content.pack(fill=BOTH, expand=True, pady=(8, 0))
            self.toggle_btn.configure(text='▼')
            
    def is_collapsed(self):
        """Check if frame is collapsed."""
        return self._collapsed
        
    def expand(self):
        """Expand the frame."""
        if self._collapsed:
            self._toggle()
            
    def collapse(self):
        """Collapse the frame."""
        if not self._collapsed:
            self._toggle()


class Badge(Label):
    """
    A small badge/pill for displaying counts or status.
    """
    
    def __init__(self, parent, text='', color='primary', **kwargs):
        """
        Initialize Badge.
        
        Args:
            parent: Parent widget.
            text (str): Badge text.
            color (str): Color name from COLORS.
            **kwargs: Additional Label arguments.
        """
        style = Style(parent)
        
        bg_color = COLORS.get(color, COLORS['primary'])
        fg_color = get_contrast_color(bg_color)
        
        style_name = f'Badge.{color}.TLabel'
        style.configure(style_name,
                       background=bg_color,
                       foreground=fg_color,
                       padding=(8, 2),
                       font=('Segoe UI', 8, 'bold'))
        
        super().__init__(parent, text=text, style=style_name, **kwargs)


def apply_modern_style(root):
    """
    Apply modern styling to all ttk widgets in the application.
    
    Args:
        root: The root Tk window.
    """
    style = Style(root)
    
    # Try to use a modern base theme
    available_themes = style.theme_names()
    if 'clam' in available_themes:
        style.theme_use('clam')
    elif 'vista' in available_themes:
        style.theme_use('vista')
        
    # Configure common styles
    style.configure('TButton',
                   padding=(12, 6),
                   font=('Segoe UI', 9))
    
    style.configure('TLabel',
                   font=('Segoe UI', 9))
    
    style.configure('TEntry',
                   padding=(8, 4),
                   font=('Segoe UI', 9))
    
    style.configure('TCombobox',
                   padding=(8, 4),
                   font=('Segoe UI', 9))
    
    style.configure('TCheckbutton',
                   font=('Segoe UI', 9))
    
    style.configure('TRadiobutton',
                   font=('Segoe UI', 9))
    
    style.configure('TNotebook',
                   tabmargins=(2, 5, 2, 0))
    
    style.configure('TNotebook.Tab',
                   padding=(12, 4),
                   font=('Segoe UI', 9))
    
    style.configure('Treeview',
                   font=('Segoe UI', 9),
                   rowheight=24)
    
    style.configure('Treeview.Heading',
                   font=('Segoe UI', 9, 'bold'),
                   padding=(8, 4))
    
    # Map hover/active states
    style.map('TButton',
             background=[('active', COLORS['gray_200'])])
    
    style.map('Treeview',
             background=[('selected', COLORS['primary_light'])],
             foreground=[('selected', COLORS['gray_800'])])
