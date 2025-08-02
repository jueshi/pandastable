        try:
            # Suppress warnings about tight_layout
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.fig.tight_layout()
            self.fig.subplots_adjust(top=0.9)
            if by != '':
                self.fig.subplots_adjust(right=0.9)
        except:
            self.fig.subplots_adjust(left=0.1, right=0.9, top=0.89,
                                     bottom=0.1, hspace=.4/scf, wspace=.2/scf)
            print('tight_layout failed')
