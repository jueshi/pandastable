"""
CSV Browser - Correlation Analysis Methods
"""
import os
import traceback
import tkinter as tk
from tkinter import ttk, messagebox


class CorrelationAnalysisMixin:
    """Mixin class for correlation analysis functionality in CSVBrowser"""

    def save_correlation_analysis(self):
        """Save correlation analysis for the selected CSV file"""
        if self.current_file is None or not hasattr(self, 'csv_table'):
            messagebox.showwarning("Warning", "Please load a CSV file first")
            return

        try:
            # Get the current DataFrame
            df = self.csv_table.model.df

            # Save current plot columns before analysis
            if hasattr(self, 'plot_utils'):
                self.plot_utils.save_current_plot_columns()

            # Get numeric columns that have variation
            numeric_columns = self.plot_utils.get_numeric_varying_columns(df)

            if not numeric_columns:
                messagebox.showwarning(
                    "Warning",
                    "No numeric columns with variation found in the dataset"
                )
                return

            # Create dialog for selecting target column
            dialog = tk.Toplevel(self)
            dialog.title("Select Target Column")
            dialog.transient(self)
            dialog.grab_set()

            # Add instructions
            ttk.Label(
                dialog,
                text="Select a target column for correlation analysis:",
                padding=10
            ).pack()

            # Variable to store selected column
            target_col = tk.StringVar()

            # Create combobox for column selection
            column_combo = ttk.Combobox(
                dialog,
                textvariable=target_col,
                values=numeric_columns,
                state="readonly",
                width=50
            )
            column_combo.pack(padx=10, pady=5)

            # Set default selection
            if numeric_columns:
                column_combo.set(numeric_columns[0])

            # Button frame
            button_frame = ttk.Frame(dialog)
            button_frame.pack(pady=10)

            def on_ok():
                try:
                    # Get selected target column
                    target_col_value = column_combo.get()

                    if not target_col_value:
                        messagebox.showwarning(
                            "Warning",
                            "Please select a target column"
                        )
                        return

                    # Get correlation analysis
                    corr_df, data_df = self.plot_utils.get_top_correlated_columns(
                        df, target_col_value, top_n=10
                    )

                    if corr_df.empty:
                        messagebox.showwarning(
                            "Warning",
                            "No correlations found for the selected column"
                        )
                        return

                    # Create base directory for saving analysis
                    base_name = os.path.splitext(os.path.basename(self.current_file))[0]
                    base_path = os.path.join(
                        os.path.dirname(self.current_file),
                        f"{base_name}_correlation_analysis"
                    )

                    # Create directory if it doesn't exist
                    os.makedirs(base_path, exist_ok=True)

                    # Save correlation data to CSV
                    corr_file = os.path.join(base_path, f"correlations_{target_col_value}.csv")
                    corr_df.to_csv(corr_file, index=False)
                    print(f"Saved correlation data to: {corr_file}")

                    # Create correlation plots
                    self.plot_utils.create_correlation_plots(
                        data_df, target_col_value, corr_df, base_path
                    )

                    # Create and save correlation heatmap
                    heatmap_fig = self.plot_utils.plot_correlation_heatmap(
                        data_df,
                        columns=[target_col_value] + list(corr_df['Column'])
                    )
                    if heatmap_fig:
                        heatmap_file = os.path.join(base_path, f"heatmap_{target_col_value}.png")
                        heatmap_fig.savefig(heatmap_file, dpi=300, bbox_inches='tight')
                        print(f"Saved heatmap to: {heatmap_file}")

                    # Create and save scatter matrix
                    scatter_fig = self.plot_utils.plot_scatter_matrix(
                        data_df,
                        columns=[target_col_value] + list(corr_df['Column'][:5])
                    )
                    if scatter_fig:
                        scatter_file = os.path.join(base_path, f"scatter_matrix_{target_col_value}.png")
                        scatter_fig.savefig(scatter_file, dpi=300, bbox_inches='tight')
                        print(f"Saved scatter matrix to: {scatter_file}")

                    messagebox.showinfo(
                        "Success",
                        f"Correlation analysis saved to:\n{base_path}"
                    )

                    # Restore plot columns after analysis
                    if hasattr(self, 'plot_utils'):
                        self.plot_utils.restore_plot_columns()

                        # If plot viewer is open, update it
                        if hasattr(self.csv_table, 'pf') and self.csv_table.pf is not None:
                            self.plot_utils._safe_replot_with_index_preservation(self.csv_table.pf)

                except Exception as e:
                    messagebox.showerror(
                        "Error",
                        f"Error during correlation analysis:\n{str(e)}"
                    )
                    traceback.print_exc()
                finally:
                    dialog.destroy()

            def on_cancel():
                dialog.destroy()
                # Restore plot columns on cancel
                if hasattr(self, 'plot_utils'):
                    self.plot_utils.restore_plot_columns()

            ttk.Button(
                button_frame,
                text="OK",
                command=on_ok
            ).pack(side="left", padx=5)

            ttk.Button(
                button_frame,
                text="Cancel",
                command=on_cancel
            ).pack(side="left", padx=5)

            # Center the dialog
            dialog.update_idletasks()
            width = dialog.winfo_width()
            height = dialog.winfo_height()
            x = (dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (dialog.winfo_screenheight() // 2) - (height // 2)
            dialog.geometry(f"{width}x{height}+{x}+{y}")

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Error setting up correlation analysis:\n{str(e)}"
            )
            traceback.print_exc()
            # Restore plot columns on error
            if hasattr(self, 'plot_utils'):
                self.plot_utils.restore_plot_columns()
