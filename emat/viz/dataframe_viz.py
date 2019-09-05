

import numpy
import pandas
import plotly.graph_objs as go
from ipywidgets import HBox, VBox, Dropdown, Label, Text
from . import colors
from ..util.naming import clean_name

class DataFrameViewer(HBox):

	def __init__(
			self,
			df,
			selection=None,
			box=None,
			scope=None,
			target_marker_opacity=1000,
			minimum_marker_opacity=0.25,
	):
		self.df = df

		self.selection = selection
		self.box = box
		self.scope = scope

		self._alt_selections = {}

		self.x_axis_choose = Dropdown(
			options=self.df.columns,
			#description='X Axis',
			value=self.df.columns[0],
		)

		self.x_axis_scale = Dropdown(
			options=['linear',],
			value='linear',
		)

		self.y_axis_choose = Dropdown(
			options=self.df.columns,
			#description='Y Axis',
			value=self.df.columns[-1],
		)

		self.y_axis_scale = Dropdown(
			options=['linear',],
			value='linear',
		)

		self.selection_choose = Dropdown(
			options=['None', 'Box', 'Expr'] + list(self._alt_selections.keys()),
			value='None',
		)

		self.selection_expr = Text(
			value='True',
			disabled=True,
		)

		self.axis_choose = VBox(
			[
				Label("X Axis"),
				self.x_axis_choose,
				self.x_axis_scale,
				Label("Y Axis"),
				self.y_axis_choose,
				self.y_axis_scale,
				Label("Selection"),
				self.selection_choose,
				self.selection_expr,
			],
			layout=dict(
				overflow='hidden',
			)
		)

		self.minimum_marker_opacity = minimum_marker_opacity
		self.target_marker_opacity = target_marker_opacity
		marker_opacity = self._compute_marker_opacity()

		self._x_data_range = [0,1]
		self._y_data_range = [0,1]

		self.scattergraph = go.Scattergl(
			x=None,
			y=None,
			mode = 'markers',
			marker=dict(
				opacity=marker_opacity[0],
				color=colors.DEFAULT_BASE_COLOR,
			),
		)

		self.x_hist = go.Histogram(
			x=None,
			name='x density',
			marker=dict(
				color=colors.DEFAULT_BASE_COLOR,
				#opacity=0.7,
			),
			yaxis='y2',
			bingroup='xxx',
		)

		self.y_hist = go.Histogram(
			y=None,
			name='y density',
			marker=dict(
				color=colors.DEFAULT_BASE_COLOR,
				#opacity=0.7,
			),
			xaxis='x2',
			bingroup='yyy',
		)

		self.scattergraph_s = go.Scattergl(
			x=None,
			y=None,
			mode = 'markers',
			marker=dict(
				opacity=marker_opacity[1],
				color=colors.DEFAULT_HIGHLIGHT_COLOR,
			),
		)

		self.x_hist_s = go.Histogram(
			x=None,
			marker=dict(
				color=colors.DEFAULT_HIGHLIGHT_COLOR,
				#opacity=0.7,
			),
			yaxis='y2',
			bingroup='xxx',
		)

		self.y_hist_s = go.Histogram(
			y=None,
			marker=dict(
				color=colors.DEFAULT_HIGHLIGHT_COLOR,
				#opacity=0.7,
			),
			xaxis='x2',
			bingroup='yyy',
		)

		self.graph = go.FigureWidget([
			self.scattergraph,
			self.x_hist,
			self.y_hist,
			self.scattergraph_s,
			self.x_hist_s,
			self.y_hist_s,
		])


		self.graph.layout=dict(
			xaxis=dict(
				domain=[0, 0.85],
				showgrid=True,
				#title=self.df.columns[0],
			),
			yaxis=dict(
				domain=[0, 0.85],
				showgrid=True,
				#title=self.df.columns[-1],
			),

			xaxis2=dict(
				domain=[0.85, 1],
				showgrid=True,
				zeroline=True,
				zerolinecolor='#FFF',
				zerolinewidth=4,
			),
			yaxis2=dict(
				domain=[0.85, 1],
				showgrid=True,
				zeroline=True,
				zerolinecolor='#FFF',
				zerolinewidth=4,
			),

			barmode="overlay",
			showlegend=False,
			margin=dict(l=10, r=10, t=10, b=10),
		)

		self.x_axis_choose.observe(self._observe_change_column_x, names='value')
		self.y_axis_choose.observe(self._observe_change_column_y, names='value')
		self.selection_choose.observe(self._on_change_selection_choose, names='value')
		self.selection_expr.observe(self._on_change_selection_expr, names='value')

		self.set_x(self.df.columns[0])
		self.set_y(self.df.columns[-1])
		self.draw_box()

		super().__init__(
			[
				self.graph,
				self.axis_choose,
			],
			layout=dict(
				align_items='center',
			)
		)

	def _get_shortname(self, name):
		if self.scope is None:
			return name
		return self.scope.shortname(name)

	def _compute_marker_opacity(self):
		if self.selection is None:
			marker_opacity = 1.0
			if len(self.df) > self.target_marker_opacity:
				marker_opacity = self.target_marker_opacity / len(self.df)
			if marker_opacity < self.minimum_marker_opacity:
				marker_opacity = self.minimum_marker_opacity
			return marker_opacity, 1.0
		else:
			marker_opacity = [1.0, 1.0]
			n_selected = int(self.selection.sum())
			n_unselect = len(self.df) - n_selected
			if n_unselect > self.target_marker_opacity:
				marker_opacity[0] = self.target_marker_opacity / n_unselect
			if marker_opacity[0] < self.minimum_marker_opacity:
				marker_opacity[0] = self.minimum_marker_opacity

			if n_selected > self.target_marker_opacity:
				marker_opacity[1] = self.target_marker_opacity / n_selected
			if marker_opacity[1] < self.minimum_marker_opacity:
				marker_opacity[1] = self.minimum_marker_opacity
			return marker_opacity

	@property
	def _x_data_width(self):
		w = self._x_data_range[1] - self._x_data_range[0]
		if w > 0:
			return w
		return 1

	@property
	def _y_data_width(self):
		w = self._y_data_range[1] - self._y_data_range[0]
		if w > 0:
			return w
		return 1

	def _observe_change_column_x(self, payload):
		self.set_x(payload['new'])

	def _observe_change_column_y(self, payload):
		self.set_y(payload['new'])

	def __manage_categorical(self, x):
		x_categories = None
		x_ticktext = None
		x_tickvals = None
		if not isinstance(x, pandas.Series):
			x = pandas.Series(x)
		if numpy.issubdtype(x.dtype, numpy.bool_):
			x = x.astype('category')
		if isinstance(x.dtype, pandas.CategoricalDtype):
			x_categories = x.cat.categories
			codes = x.cat.codes
			x = codes.astype(float)
			s_ = x.size * 0.01
			s_ = s_ / (1 + s_)
			epsilon = 0.05 + 0.20 * s_
			x = x + numpy.random.uniform(-epsilon, epsilon, size=x.shape)
			x_tickmode = 'array'
			x_ticktext = list(x_categories)
			x_tickvals = list(range(len(x_ticktext)))

		return x, x_ticktext, x_tickvals

	def set_x(self, col):
		"""
		Set the new X axis data.

		Args:
			col (str or array-like):
				The name of the new `x` column in `df`, or a
				computed array or pandas.Series of values.
		"""
		with self.graph.batch_update():
			if isinstance(col, str):
				x = self.df[col]
				self.graph.layout.xaxis.title = self._get_shortname(col)
			else:
				x = col
				try:
					self.graph.layout.xaxis.title = self._get_shortname(col.name)
				except:
					pass

			x, x_ticktext, x_tickvals = self.__manage_categorical(x)
			self._x = x
			self._x_ticktext = x_ticktext or []
			self._x_tickvals = x_tickvals or []

			if self.selection is None:
				self.graph.data[0].x = x
				self.graph.data[3].x = None
				self.graph.data[1].x = x
				self.graph.data[4].x = None
			else:
				self.graph.data[0].x = x[~self.selection]
				self.graph.data[3].x = x[self.selection]
				self.graph.data[1].x = x
				self.graph.data[4].x = x[self.selection]
			if x_ticktext is not None:
				self._x_data_range = [x.min(), x.max()]
				self.graph.layout.xaxis.range = (
					self._x_data_range[0] - 0.3,
					self._x_data_range[1] + 0.3,
				)
				self.graph.layout.xaxis.tickmode = 'array'
				self.graph.layout.xaxis.ticktext = x_ticktext
				self.graph.layout.xaxis.tickvals = x_tickvals
				self.graph.data[1].xbins = dict(
					start=-0.25, end=self._x_data_range[1] + 0.25, size=0.5,
				)
				self.graph.data[1].autobinx = False
			else:
				self._x_data_range = [x.min(), x.max()]
				self.graph.layout.xaxis.range = (
					self._x_data_range[0] - self._x_data_width * 0.07,
					self._x_data_range[1] + self._x_data_width * 0.07,
				)
				self.graph.layout.xaxis.tickmode = None
				self.graph.layout.xaxis.ticktext = None
				self.graph.layout.xaxis.tickvals = None
				self.graph.data[1].xbins = None
				self.graph.data[1].autobinx = True
			self.draw_box()

	def set_y(self, col):
		"""
		Set the new Y axis data.

		Args:
			col (str or array-like):
				The name of the new `y` column in `df`, or a
				computed array or pandas.Series of values.
		"""
		with self.graph.batch_update():
			if isinstance(col, str):
				y = self.df[col]
				self.graph.layout.yaxis.title = self._get_shortname(col)
			else:
				y = col
				try:
					self.graph.layout.yaxis.title = self._get_shortname(col.name)
				except:
					pass

			y, y_ticktext, y_tickvals = self.__manage_categorical(y)
			self._y = y
			self._y_ticktext = y_ticktext or []
			self._y_tickvals = y_tickvals or []

			if self.selection is None:
				self.graph.data[0].y = y
				self.graph.data[3].y = None
				self.graph.data[2].y = y
				self.graph.data[5].y = None
			else:
				self.graph.data[0].y = y[~self.selection]
				self.graph.data[3].y = y[self.selection]
				self.graph.data[2].y = y
				self.graph.data[5].y = y[self.selection]
			if y_ticktext is not None:
				self._y_data_range = [y.min(), y.max()]
				self.graph.layout.yaxis.range = (
					self._y_data_range[0] - 0.3,
					self._y_data_range[1] + 0.3,
				)
				self.graph.layout.yaxis.tickmode = 'array'
				self.graph.layout.yaxis.ticktext = y_ticktext
				self.graph.layout.yaxis.tickvals = y_tickvals
				self.graph.data[2].ybins = dict(
					start=-0.25, end=self._y_data_range[1] + 0.25, size=0.5,
				)
				self.graph.data[2].autobiny = False
			else:
				self._y_data_range = [y.min(), y.max()]
				self.graph.layout.yaxis.range = (
					self._y_data_range[0] - self._y_data_width * 0.07,
					self._y_data_range[1] + self._y_data_width * 0.07,
				)
				self.graph.layout.yaxis.tickmode = None
				self.graph.layout.yaxis.ticktext = None
				self.graph.layout.yaxis.tickvals = None
				self.graph.data[2].ybins = None
				self.graph.data[2].autobiny = True

			self.draw_box()

	def change_selection(self, new_selection):
		if new_selection is None:
			self.selection = None
			# Update Selected Portion of Scatters
			x = self._x
			y = self._y
			with self.graph.batch_update():
				self.graph.data[0].x = x
				self.graph.data[0].y = y
				self.graph.data[3].x = None
				self.graph.data[3].y = None
				marker_opacity = self._compute_marker_opacity()
				self.graph.data[0].marker.opacity = marker_opacity[0]
				self.graph.data[3].marker.opacity = marker_opacity[1]
				# Update Selected Portion of Histograms
				self.graph.data[4].x = None
				self.graph.data[5].y = None
				self.draw_box()
			return

		if new_selection.size != len(self.df):
			raise ValueError(f"new selection size ({new_selection.size}) "
							 f"does not match length of data ({len(self.df)})")
		self.selection = new_selection
		with self.graph.batch_update():
			# Update Selected Portion of Scatters
			x = self._x
			y = self._y
			# x = self.df[self.x_axis_choose.value]
			# y = self.df[self.y_axis_choose.value]
			self.graph.data[0].x = x[~self.selection]
			self.graph.data[0].y = y[~self.selection]
			self.graph.data[3].x = x[self.selection]
			self.graph.data[3].y = y[self.selection]
			marker_opacity = self._compute_marker_opacity()
			self.graph.data[0].marker.opacity = marker_opacity[0]
			self.graph.data[3].marker.opacity = marker_opacity[1]
			# Update Selected Portion of Histograms
			self.graph.data[4].x = x[self.selection]
			self.graph.data[5].y = y[self.selection]
			self.draw_box()

	def draw_box(self, box=None):
		from ..scope.box import Bounds
		x_label = self.x_axis_choose.value
		y_label = self.y_axis_choose.value

		if box is None:
			box = self.box
		if box is None:
			self.graph.layout.shapes = []
		else:
			if x_label in box.thresholds or y_label in box.thresholds:
				x_lo, x_hi = None, None
				thresh = box.thresholds.get(x_label)
				if isinstance(thresh, Bounds):
					x_lo, x_hi = thresh
				if isinstance(thresh, set):
					x_lo, x_hi = [], []
					for tickval, ticktext in zip(self._x_tickvals, self._x_ticktext):
						if ticktext in thresh:
							x_lo.append(tickval-0.3)
							x_hi.append(tickval+0.3)
				if x_lo is None:
					x_lo = self.df[x_label].min()-self._x_data_width * 0.02
				if x_hi is None:
					x_hi = self.df[x_label].max()+self._x_data_width * 0.02
				if not isinstance(x_lo, list):
					x_lo = [x_lo]
				if not isinstance(x_hi, list):
					x_hi = [x_hi]

				y_lo, y_hi = None, None
				thresh = box.thresholds.get(y_label)
				if isinstance(thresh, Bounds):
					y_lo, y_hi = thresh
				if isinstance(thresh, set):
					y_lo, y_hi = [], []
					for tickval, ticktext in zip(self._y_tickvals, self._y_ticktext):
						if ticktext in thresh:
							y_lo.append(tickval-0.3)
							y_hi.append(tickval+0.3)
				if y_lo is None:
					y_lo = self.df[y_label].min()-self._y_data_width * 0.02
				if y_hi is None:
					y_hi = self.df[y_label].max()+self._y_data_width * 0.02
				if not isinstance(y_lo, list):
					y_lo = [y_lo]
				if not isinstance(y_hi, list):
					y_hi = [y_hi]

				x_pairs = list(zip(x_lo, x_hi))
				y_pairs = list(zip(y_lo, y_hi))

				background_shapes = [
					# Rectangle background color
					go.layout.Shape(
						type="rect",
						xref="x1",
						yref="y1",
						x0=x_pair[0],
						y0=y_pair[0],
						x1=x_pair[1],
						y1=y_pair[1],
						line=dict(
							width=0,
						),
						fillcolor=colors.DEFAULT_BOX_BG_COLOR,
						opacity=0.2,
						layer="below",
					)
					for x_pair in x_pairs
					for y_pair in y_pairs
				]

				foreground_shapes = [
					# Rectangle reference to the axes
					go.layout.Shape(
						type="rect",
						xref="x1",
						yref="y1",
						x0=x_pair[0],
						y0=y_pair[0],
						x1=x_pair[1],
						y1=y_pair[1],
						line=dict(
							width=1,
							color=colors.DEFAULT_BOX_LINE_COLOR,
						),
						fillcolor='rgba(0,0,0,0)',
						opacity=1.0,
					)
					for x_pair in x_pairs
					for y_pair in y_pairs
				]

				self.graph.layout.shapes=background_shapes+foreground_shapes
			else:
				self.graph.layout.shapes=[]

	def _selection_eval(self, txt):
		df = self.df.rename(columns={i: clean_name(i) for i in self.df.columns})
		return df.eval(txt).astype(bool)

	def _on_change_selection_choose(self, payload):
		if payload['new'] != 'Expr':
			self.selection_expr.disabled = True
		if payload['new'] == 'Expr':
			self.selection_expr.disabled = False
			self._on_change_selection_expr({'new':self.selection_expr.value})
		elif payload['new'] == 'Box':
			self.change_selection(self.box.inside(self.df))
		elif payload['new'] == 'None':
			self.change_selection(None)
		else:
			self.change_selection(self._alt_selections[payload['new']])

	def _on_change_selection_expr(self, payload):
		expression = payload['new']
		try:
			sel = self._selection_eval(expression)
		except Exception as err:
			#print("FAILED ON EVAL\n",expression, err)
			pass
		else:
			try:
				self.change_selection(sel)
			except Exception as err:
				#print("FAILED ON SETTING\n", expression, err)
				pass
			else:
				#print("PASSED", expression)
				pass

	def _on_box_change(self, selection=None):
		if self.selection_choose.value == 'Box':
			if selection is None:
				selection = self.box.inside(self.df)
			self.change_selection(selection)
		else:
			with self.graph.batch_update():
				self.draw_box()

	def add_alt_selection(self, key, value):
		"""
		Add a new possible alternative selection vector.

		Parameters
		----------
		key : str
			An identifier for the new selection vector.
		value : array-like of bool
			A vector of boolean values giving the selection.
		"""
		if value.size != len(self.df):
			raise ValueError(f"value size ({value.size}) "
							 f"does not match length of data ({len(self.df)})")
		self._alt_selections[key] = value
		self.selection_choose.options = ['None', 'Box', 'Expr'] + list(self._alt_selections.keys())
