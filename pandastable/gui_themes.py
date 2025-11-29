#!/usr/bin/env python
"""
    Modern GUI themes and styling for pandastable.
    
    This module provides:
    - Modern color themes with improved contrast and accessibility
    - Consistent styling utilities
    - Theme management functions
    
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
except:
    from Tkinter import *
    from ttk import *


# Modern color palette with improved accessibility
COLORS = {
    # Primary colors
    'primary': '#2563EB',           # Blue 600
    'primary_hover': '#1D4ED8',     # Blue 700
    'primary_light': '#DBEAFE',     # Blue 100
    
    # Secondary colors
    'secondary': '#64748B',         # Slate 500
    'secondary_hover': '#475569',   # Slate 600
    
    # Success/Error/Warning
    'success': '#16A34A',           # Green 600
    'success_light': '#DCFCE7',     # Green 100
    'error': '#DC2626',             # Red 600
    'error_light': '#FEE2E2',       # Red 100
    'warning': '#D97706',           # Amber 600
    'warning_light': '#FEF3C7',     # Amber 100
    
    # Neutral colors
    'white': '#FFFFFF',
    'gray_50': '#F9FAFB',
    'gray_100': '#F3F4F6',
    'gray_200': '#E5E7EB',
    'gray_300': '#D1D5DB',
    'gray_400': '#9CA3AF',
    'gray_500': '#6B7280',
    'gray_600': '#4B5563',
    'gray_700': '#374151',
    'gray_800': '#1F2937',
    'gray_900': '#111827',
    
    # Dark mode colors
    'dark_bg': '#1E1E2E',
    'dark_surface': '#2D2D3D',
    'dark_border': '#3D3D4D',
    'dark_text': '#E4E4E7',
    'dark_text_secondary': '#A1A1AA',
}


# Modern themes with comprehensive styling
MODERN_THEMES = {
    'light': {
        # Table colors
        'cellbackgr': COLORS['white'],
        'grid_color': COLORS['gray_200'],
        'textcolor': COLORS['gray_800'],
        'rowselectedcolor': COLORS['primary_light'],
        'colselectedcolor': COLORS['gray_100'],
        'multipleselectioncolor': '#E0F2FE',  # Sky 100
        'boxoutlinecolor': COLORS['primary'],
        
        # Header colors - dark background with white text for visibility
        'colheaderbgcolor': '#4B5563',  # gray-600
        'colheaderfgcolor': '#FFFFFF',  # white
        'rowheaderbgcolor': '#E5E7EB',  # gray-200
        'rowheaderfgcolor': '#1F2937',  # gray-800
        
        # Entry colors
        'entrybackgr': COLORS['white'],
        
        # UI element colors
        'toolbar_bg': COLORS['gray_50'],
        'statusbar_bg': COLORS['gray_100'],
        'button_bg': COLORS['primary'],
        'button_fg': COLORS['white'],
        'button_hover': COLORS['primary_hover'],
    },
    
    'dark': {
        # Table colors
        'cellbackgr': COLORS['dark_bg'],
        'grid_color': COLORS['dark_border'],
        'textcolor': COLORS['dark_text'],
        'rowselectedcolor': '#3B82F6',  # Blue 500
        'colselectedcolor': COLORS['dark_surface'],
        'multipleselectioncolor': '#1E3A5F',
        'boxoutlinecolor': '#60A5FA',  # Blue 400
        
        # Header colors
        'colheaderbgcolor': COLORS['dark_surface'],
        'colheaderfgcolor': COLORS['dark_text'],
        'rowheaderbgcolor': '#252535',
        'rowheaderfgcolor': COLORS['dark_text_secondary'],
        
        # Entry colors
        'entrybackgr': COLORS['dark_surface'],
        
        # UI element colors
        'toolbar_bg': COLORS['dark_surface'],
        'statusbar_bg': COLORS['dark_surface'],
        'button_bg': '#3B82F6',
        'button_fg': COLORS['white'],
        'button_hover': '#2563EB',
    },
    
    'ocean': {
        # Table colors
        'cellbackgr': '#F0F9FF',      # Sky 50
        'grid_color': '#BAE6FD',       # Sky 200
        'textcolor': '#0C4A6E',        # Sky 900
        'rowselectedcolor': '#7DD3FC', # Sky 300
        'colselectedcolor': '#E0F2FE', # Sky 100
        'multipleselectioncolor': '#BAE6FD',
        'boxoutlinecolor': '#0284C7',  # Sky 600
        
        # Header colors
        'colheaderbgcolor': '#0EA5E9', # Sky 500
        'colheaderfgcolor': COLORS['white'],
        'rowheaderbgcolor': '#E0F2FE',
        'rowheaderfgcolor': '#0369A1',
        
        # Entry colors
        'entrybackgr': COLORS['white'],
        
        # UI element colors
        'toolbar_bg': '#E0F2FE',
        'statusbar_bg': '#F0F9FF',
        'button_bg': '#0284C7',
        'button_fg': COLORS['white'],
        'button_hover': '#0369A1',
    },
    
    'forest': {
        # Table colors
        'cellbackgr': '#F0FDF4',       # Green 50
        'grid_color': '#BBF7D0',       # Green 200
        'textcolor': '#14532D',        # Green 900
        'rowselectedcolor': '#86EFAC', # Green 300
        'colselectedcolor': '#DCFCE7', # Green 100
        'multipleselectioncolor': '#BBF7D0',
        'boxoutlinecolor': '#16A34A',  # Green 600
        
        # Header colors
        'colheaderbgcolor': '#22C55E', # Green 500
        'colheaderfgcolor': COLORS['white'],
        'rowheaderbgcolor': '#DCFCE7',
        'rowheaderfgcolor': '#15803D',
        
        # Entry colors
        'entrybackgr': COLORS['white'],
        
        # UI element colors
        'toolbar_bg': '#DCFCE7',
        'statusbar_bg': '#F0FDF4',
        'button_bg': '#16A34A',
        'button_fg': COLORS['white'],
        'button_hover': '#15803D',
    },
    
    'sunset': {
        # Table colors
        'cellbackgr': '#FFFBEB',       # Amber 50
        'grid_color': '#FDE68A',       # Amber 200
        'textcolor': '#78350F',        # Amber 900
        'rowselectedcolor': '#FCD34D', # Amber 300
        'colselectedcolor': '#FEF3C7', # Amber 100
        'multipleselectioncolor': '#FDE68A',
        'boxoutlinecolor': '#D97706',  # Amber 600
        
        # Header colors
        'colheaderbgcolor': '#F59E0B', # Amber 500
        'colheaderfgcolor': COLORS['white'],
        'rowheaderbgcolor': '#FEF3C7',
        'rowheaderfgcolor': '#B45309',
        
        # Entry colors
        'entrybackgr': COLORS['white'],
        
        # UI element colors
        'toolbar_bg': '#FEF3C7',
        'statusbar_bg': '#FFFBEB',
        'button_bg': '#D97706',
        'button_fg': COLORS['white'],
        'button_hover': '#B45309',
    },
    
    'high_contrast': {
        # Table colors - Maximum contrast for accessibility
        'cellbackgr': COLORS['white'],
        'grid_color': COLORS['gray_900'],
        'textcolor': COLORS['gray_900'],
        'rowselectedcolor': '#FBBF24',  # Amber 400
        'colselectedcolor': '#FEF3C7',
        'multipleselectioncolor': '#FDE68A',
        'boxoutlinecolor': COLORS['gray_900'],
        
        # Header colors
        'colheaderbgcolor': COLORS['gray_900'],
        'colheaderfgcolor': COLORS['white'],
        'rowheaderbgcolor': COLORS['gray_200'],
        'rowheaderfgcolor': COLORS['gray_900'],
        
        # Entry colors
        'entrybackgr': COLORS['white'],
        
        # UI element colors
        'toolbar_bg': COLORS['gray_200'],
        'statusbar_bg': COLORS['gray_100'],
        'button_bg': COLORS['gray_900'],
        'button_fg': COLORS['white'],
        'button_hover': COLORS['gray_700'],
    },
}


# TTK Style configurations for modern look
TTK_STYLES = {
    'light': {
        'TButton': {
            'configure': {
                'padding': (12, 6),
                'font': ('Segoe UI', 9),
            },
        },
        'TLabel': {
            'configure': {
                'font': ('Segoe UI', 9),
            },
        },
        'TEntry': {
            'configure': {
                'padding': (8, 4),
                'font': ('Segoe UI', 9),
            },
        },
        'TCombobox': {
            'configure': {
                'padding': (8, 4),
                'font': ('Segoe UI', 9),
            },
        },
        'TNotebook': {
            'configure': {
                'tabmargins': (2, 5, 2, 0),
            },
        },
        'TNotebook.Tab': {
            'configure': {
                'padding': (12, 4),
                'font': ('Segoe UI', 9),
            },
        },
        'Treeview': {
            'configure': {
                'font': ('Segoe UI', 9),
                'rowheight': 24,
            },
        },
        'Treeview.Heading': {
            'configure': {
                'font': ('Segoe UI', 9, 'bold'),
                'padding': (8, 4),
            },
        },
    },
    'dark': {
        'TButton': {
            'configure': {
                'padding': (12, 6),
                'font': ('Segoe UI', 9),
            },
        },
        'TLabel': {
            'configure': {
                'font': ('Segoe UI', 9),
            },
        },
        'TEntry': {
            'configure': {
                'padding': (8, 4),
                'font': ('Segoe UI', 9),
            },
        },
    },
}


class ThemeManager:
    """
    Manages theme application and switching for pandastable GUI.
    
    Attributes:
        current_theme (str): Name of the currently active theme.
        style (ttk.Style): The ttk Style object for widget styling.
    """
    
    def __init__(self, root=None):
        """
        Initialize the ThemeManager.
        
        Args:
            root: The root Tk window (optional).
        """
        self.current_theme = 'light'
        self.style = None
        self.root = root
        self._callbacks = []
        
    def initialize_style(self, root=None):
        """
        Initialize the ttk Style object.
        
        Args:
            root: The root Tk window.
        """
        if root:
            self.root = root
        if self.root:
            self.style = Style(self.root)
            
    def get_available_themes(self):
        """
        Get list of available theme names.
        
        Returns:
            list: List of theme name strings.
        """
        return list(MODERN_THEMES.keys())
    
    def get_theme(self, name=None):
        """
        Get theme configuration by name.
        
        Args:
            name (str): Theme name. If None, returns current theme.
            
        Returns:
            dict: Theme configuration dictionary.
        """
        if name is None:
            name = self.current_theme
        return MODERN_THEMES.get(name, MODERN_THEMES['light'])
    
    def apply_theme(self, name, table=None):
        """
        Apply a theme to the table and update TTK styles.
        
        Args:
            name (str): Theme name to apply.
            table: The Table instance to apply theme to.
        """
        if name not in MODERN_THEMES:
            name = 'light'
            
        self.current_theme = name
        theme = MODERN_THEMES[name]
        
        # Apply to table if provided
        if table:
            for key, value in theme.items():
                if hasattr(table, key):
                    setattr(table, key, value)
            table.redraw()
            
        # Apply TTK styles
        self._apply_ttk_styles(name)
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(name, theme)
            except Exception:
                pass
                
    def _apply_ttk_styles(self, theme_name):
        """
        Apply TTK widget styles for the given theme.
        
        Args:
            theme_name (str): Theme name.
        """
        if not self.style:
            return
            
        # Get style config, default to light if not found
        style_config = TTK_STYLES.get(theme_name, TTK_STYLES.get('light', {}))
        
        for widget_style, config in style_config.items():
            if 'configure' in config:
                try:
                    self.style.configure(widget_style, **config['configure'])
                except Exception:
                    pass
            if 'map' in config:
                try:
                    self.style.map(widget_style, **config['map'])
                except Exception:
                    pass
                    
    def register_callback(self, callback):
        """
        Register a callback to be called when theme changes.
        
        Args:
            callback: Function(theme_name, theme_config) to call.
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)
            
    def unregister_callback(self, callback):
        """
        Unregister a theme change callback.
        
        Args:
            callback: The callback function to remove.
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)


def get_contrast_color(bg_color):
    """
    Calculate appropriate text color (black or white) for given background.
    
    Uses WCAG luminance formula for accessibility.
    
    Args:
        bg_color (str): Background color in hex format (#RRGGBB).
        
    Returns:
        str: '#000000' for dark text or '#FFFFFF' for light text.
    """
    if not bg_color or not bg_color.startswith('#'):
        return '#000000'
        
    # Remove # and parse RGB
    bg_color = bg_color.lstrip('#')
    if len(bg_color) == 3:
        bg_color = ''.join([c*2 for c in bg_color])
        
    try:
        r = int(bg_color[0:2], 16) / 255.0
        g = int(bg_color[2:4], 16) / 255.0
        b = int(bg_color[4:6], 16) / 255.0
    except (ValueError, IndexError):
        return '#000000'
    
    # Calculate relative luminance (WCAG formula)
    def adjust(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        
    luminance = 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)
    
    # Return black for light backgrounds, white for dark
    return '#000000' if luminance > 0.179 else '#FFFFFF'


def blend_colors(color1, color2, factor=0.5):
    """
    Blend two colors together.
    
    Args:
        color1 (str): First color in hex format.
        color2 (str): Second color in hex format.
        factor (float): Blend factor (0.0 = color1, 1.0 = color2).
        
    Returns:
        str: Blended color in hex format.
    """
    c1 = color1.lstrip('#')
    c2 = color2.lstrip('#')
    
    try:
        r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
        r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
    except (ValueError, IndexError):
        return color1
        
    r = int(r1 + (r2 - r1) * factor)
    g = int(g1 + (g2 - g1) * factor)
    b = int(b1 + (b2 - b1) * factor)
    
    return f'#{r:02x}{g:02x}{b:02x}'


def lighten_color(color, factor=0.2):
    """
    Lighten a color by blending with white.
    
    Args:
        color (str): Color in hex format.
        factor (float): Amount to lighten (0.0-1.0).
        
    Returns:
        str: Lightened color in hex format.
    """
    return blend_colors(color, '#FFFFFF', factor)


def darken_color(color, factor=0.2):
    """
    Darken a color by blending with black.
    
    Args:
        color (str): Color in hex format.
        factor (float): Amount to darken (0.0-1.0).
        
    Returns:
        str: Darkened color in hex format.
    """
    return blend_colors(color, '#000000', factor)


# Global theme manager instance
_theme_manager = None

def get_theme_manager():
    """
    Get the global ThemeManager instance.
    
    Returns:
        ThemeManager: The global theme manager.
    """
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


# Legacy compatibility - map old theme names to new ones
LEGACY_THEME_MAP = {
    'default': 'light',
    'bold': 'high_contrast',
}

def get_legacy_theme(name):
    """
    Get theme config using legacy theme name.
    
    Args:
        name (str): Legacy theme name.
        
    Returns:
        dict: Theme configuration (subset for backward compatibility).
    """
    mapped_name = LEGACY_THEME_MAP.get(name, name)
    theme = MODERN_THEMES.get(mapped_name, MODERN_THEMES['light'])
    
    # Return only the keys that existed in the old theme format
    legacy_keys = ['cellbackgr', 'grid_color', 'textcolor', 
                   'rowselectedcolor', 'colselectedcolor']
    return {k: theme[k] for k in legacy_keys if k in theme}
