odoo.define('purchases_dashboard', function (require) {
    'use strict';

    var kanban_widgets_purchases = require('web_kanban.widgets');

    var PurchasesDashboardGraph = kanban_widgets_purchases.AbstractField.extend({
        start: function () {
            this.graph_type = this.$node.attr('graph_type');
            this.data = JSON.parse(this.field.raw_value);
            this.display_graph();
            return this._super();
        },

        display_graph: function () {
            var self = this;
            nv.addGraph(function () {
                self.$svg = self.$el.append('<svg>');

                switch (self.graph_type) {

                    case "bar":
                        var bandera = self.data[0]
                        self.$svg.addClass('o_graph_barchart');

                        self.chart = nv.models.discreteBarChart()
                            .x(function (d) {
                                return d.label
                            })
                            .y(function (d) {
                                return d.value
                            })
                            .showValues(false)
                            .showYAxis(false)
                            .wrapLabels(true)
                            .margin({'left': 10, 'right': 0, 'top': 0, 'bottom': 40});

                        if (bandera.flag) {
                            self.chart.yAxis
                                .showMaxMin(false)
                                .tickFormat(function (d) {
                                    return "$" + d3.format(',.2f')(d)
                                });
                        }
                        else {
                            self.chart.yAxis
                                .tickFormat(d3.format(',.0f'));
                        }
                        break;

                    case "bar_stacked":
                        self.$svg.addClass('o_graph_multibarchart');
                        self.chart = nv.models.multiBarChart()
                            .reduceXTicks(false)   //If 'false', every single x-axis tick label will be rendered.
                            .rotateLabels(0)      //Angle to rotate x-axis labels.
                            .wrapLabels(true)
                            .showControls(false)   //Allow user to switch between 'Grouped' and 'Stacked' mode.
                            .groupSpacing(0.1);    //Distance between each group of bars.

                        self.chart.yAxis
                            .tickFormat(function (d) {return "$" + d3.format(',.2f')(d)});

                }
                d3.select(self.$el.find('svg')[0])
                    .datum(self.data)
                    .transition().duration(1200)
                    .call(self.chart);
                self.customize_chart();

                nv.utils.windowResize(self.on_resize);

            });
        },

        on_resize: function () {
            this.chart.update();
            this.customize_chart();
        },

        customize_chart: function () {
            if (this.graph_type === 'bar') {
                // Add classes related to time on each bar of the bar chart
                var bar_classes = _.map(this.data[0].values, function (v, k) {
                    return v.type
                });

                _.each(this.$('.nv-bar'), function (v, k) {
                    // classList doesn't work with phantomJS & addClass doesn't work with a SVG element
                    $(v).attr('class', $(v).attr('class') + ' ' + bar_classes[k]);
                });
            }
        },

        destroy: function () {
            nv.utils.offWindowResize(this.on_resize);
            this._super();
        },

    });


    kanban_widgets_purchases.registry.add('dashboard_graph_purchases', PurchasesDashboardGraph);

});