import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from './ui/tabs';
import { BarChart, Bar, PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, PieChart as PieChartIcon, BarChart3 } from 'lucide-react';
import { parseLocalDate } from '../dateUtils';

interface Expense {
  id: string;
  amount: number;
  category: string;
  description: string;
  date: string;
}

interface SpendingGraphProps {
  expenses: Expense[];
  budget: number;
  categoryTotals: { [key: string]: number };
}

const COLORS = [
  '#FF6B6B', // Red
  '#4ECDC4', // Cyan
  '#45B7D1', // Blue
  '#FFA07A', // Orange
  '#98D8C8', // Mint
  '#F7DC6F', // Yellow
  '#BB8FCE', // Purple
  '#85C1E2', // Light Blue
];

export function SpendingGraph({ expenses, budget, categoryTotals }: SpendingGraphProps) {
  const [activeTab, setActiveTab] = useState('category');

  // Prepare category data for pie and bar charts
  const categoryData = Object.entries(categoryTotals).map(([category, amount]) => ({
    name: category,
    value: amount,
    percentage: budget > 0 ? ((amount / budget) * 100).toFixed(1) : 0
  })).sort((a, b) => b.value - a.value);

  // Prepare daily spending data for line chart
  const getDailySpending = () => {
    const dailyMap: { [key: string]: number } = {};
    
    expenses.forEach(expense => {
      const date = parseLocalDate(expense.date).toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric' 
      });
      dailyMap[date] = (dailyMap[date] || 0) + expense.amount;
    });

    return Object.entries(dailyMap)
      .map(([date, amount]) => ({ date, amount }))
      .slice(-7); // Last 7 days
  };

  const dailyData = getDailySpending();

  // Custom tooltip for charts
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white/95 backdrop-blur-sm border-2 border-cyan-300 rounded-lg p-3 shadow-lg">
          <p className="font-semibold text-gray-900">{payload[0].name || payload[0].payload.name}</p>
          <p className="text-cyan-700 font-bold">${payload[0].value.toFixed(2)}</p>
          {payload[0].payload.percentage && (
            <p className="text-gray-600 text-sm">{payload[0].payload.percentage}% of budget</p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <Card className="bg-white/85 backdrop-blur-md border-2 border-cyan-300 shadow-lg">
      <CardHeader>
        <CardTitle className="text-base sm:text-lg flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-cyan-600" />
          Spending Analytics
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3 mb-4">
            <TabsTrigger value="category" className="text-xs sm:text-sm">
              <PieChartIcon className="h-4 w-4 mr-1 sm:mr-2" />
              <span className="hidden sm:inline">By Category</span>
              <span className="sm:hidden">Category</span>
            </TabsTrigger>
            <TabsTrigger value="bar" className="text-xs sm:text-sm">
              <BarChart3 className="h-4 w-4 mr-1 sm:mr-2" />
              <span className="hidden sm:inline">Bar Chart</span>
              <span className="sm:hidden">Bar</span>
            </TabsTrigger>
            <TabsTrigger value="trend" className="text-xs sm:text-sm">
              <TrendingUp className="h-4 w-4 mr-1 sm:mr-2" />
              <span className="hidden sm:inline">Daily Trend</span>
              <span className="sm:hidden">Trend</span>
            </TabsTrigger>
          </TabsList>

          {/* Pie Chart */}
          <TabsContent value="category" className="mt-4">
            {categoryData.length > 0 ? (
              <div className="space-y-4">
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={categoryData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percentage }) => `${name.split(' ')[0]} ${percentage}%`}
                      outerRadius={100}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {categoryData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                  </PieChart>
                </ResponsiveContainer>

                {/* Legend */}
                <div className="grid grid-cols-2 gap-2 mt-4">
                  {categoryData.map((item, index) => (
                    <div key={item.name} className="flex items-center gap-2 text-sm">
                      <div 
                        className="w-3 h-3 rounded-full flex-shrink-0" 
                        style={{ backgroundColor: COLORS[index % COLORS.length] }}
                      />
                      <span className="text-gray-700 truncate">{item.name}</span>
                      <span className="text-gray-900 font-semibold ml-auto">${item.value.toFixed(0)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-gray-500">
                No spending data yet. Add some expenses to see your breakdown! 📊
              </div>
            )}
          </TabsContent>

          {/* Bar Chart */}
          <TabsContent value="bar" className="mt-4">
            {categoryData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={categoryData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E0F7FA" />
                  <XAxis 
                    dataKey="name" 
                    angle={-45}
                    textAnchor="end"
                    height={80}
                    interval={0}
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="value" fill="#06B6D4" radius={[8, 8, 0, 0]}>
                    {categoryData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center py-12 text-gray-500">
                No spending data yet. Add some expenses to see your breakdown! 📊
              </div>
            )}
          </TabsContent>

          {/* Line Chart - Daily Trend */}
          <TabsContent value="trend" className="mt-4">
            {dailyData.length > 0 ? (
              <div className="space-y-4">
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={dailyData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E0F7FA" />
                    <XAxis 
                      dataKey="date" 
                      tick={{ fontSize: 12 }}
                      angle={-45}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                    <Line 
                      type="monotone" 
                      dataKey="amount" 
                      stroke="#06B6D4" 
                      strokeWidth={3}
                      dot={{ fill: '#06B6D4', r: 5 }}
                      activeDot={{ r: 7 }}
                      name="Daily Spending"
                    />
                  </LineChart>
                </ResponsiveContainer>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-2 bg-gradient-to-r from-cyan-50 to-blue-50 rounded-lg p-3 border border-cyan-200">
                  <div className="text-center">
                    <p className="text-xs text-gray-600">Average</p>
                    <p className="text-sm font-bold text-cyan-700">
                      ${dailyData.length > 0 
                        ? (dailyData.reduce((sum, d) => sum + d.amount, 0) / dailyData.length).toFixed(2)
                        : '0.00'
                      }
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-gray-600">Highest</p>
                    <p className="text-sm font-bold text-orange-600">
                      ${Math.max(...dailyData.map(d => d.amount)).toFixed(2)}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-gray-600">Lowest</p>
                    <p className="text-sm font-bold text-green-600">
                      ${Math.min(...dailyData.map(d => d.amount)).toFixed(2)}
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-gray-500">
                No spending data yet. Add some expenses to see your daily trend! 📈
              </div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
