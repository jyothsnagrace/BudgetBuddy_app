import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Calendar as CalendarIcon, DollarSign } from 'lucide-react';
import { format, isSameDay, startOfMonth, endOfMonth, eachDayOfInterval } from 'date-fns';
import { parseLocalDate } from '../dateUtils';

interface Expense {
  id: string;
  amount: number;
  category: string;
  description: string;
  date: string;
}

interface SpendingCalendarProps {
  expenses: Expense[];
}

export function SpendingCalendar({ expenses }: SpendingCalendarProps) {
  const [currentDate, setCurrentDate] = useState(new Date());

  const getDayHoverLabel = (day: Date, dayExpenses: Expense[], total: number) => {
    const dateLabel = format(day, 'EEE, MMM d, yyyy');

    if (dayExpenses.length === 0) {
      return `${dateLabel}\nNo expenses`;
    }

    const expenseLines = dayExpenses
      .map((expense) => `${expense.category} - $${expense.amount.toFixed(2)}`)
      .join('\n');

    return `${dateLabel}\nTotal: $${total.toFixed(2)}\n${expenseLines}`;
  };

  // Get expenses grouped by day
  const getExpensesForDay = (date: Date) => {
    return expenses.filter(expense => 
      isSameDay(parseLocalDate(expense.date), date)
    );
  };

  const getTotalForDay = (date: Date) => {
    const dayExpenses = getExpensesForDay(date);
    return dayExpenses.reduce((sum, expense) => sum + expense.amount, 0);
  };

  // Generate calendar days
  const monthStart = startOfMonth(currentDate);
  const monthEnd = endOfMonth(currentDate);
  const daysInMonth = eachDayOfInterval({ start: monthStart, end: monthEnd });

  // Get the day of week for the first day (0 = Sunday)
  const firstDayOfWeek = monthStart.getDay();

  // Previous/Next month navigation
  const goToPreviousMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
  };

  const goToNextMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
  };

  const goToToday = () => {
    setCurrentDate(new Date());
  };

  // Get color based on spending amount
  const getSpendingColor = (amount: number) => {
    if (amount === 0) return '';
    if (amount < 20) return 'bg-green-100 border-green-300 text-green-800';
    if (amount < 50) return 'bg-yellow-100 border-yellow-300 text-yellow-800';
    if (amount < 100) return 'bg-orange-100 border-orange-300 text-orange-800';
    return 'bg-red-100 border-red-300 text-red-800';
  };

  const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  return (
    <Card className="bg-white/85 backdrop-blur-md border-2 border-cyan-300 shadow-lg">
      <CardHeader>
        <CardTitle className="text-base sm:text-lg flex items-center gap-2">
          <CalendarIcon className="h-5 w-5 text-cyan-600" />
          Spending Calendar
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Calendar Header */}
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={goToPreviousMonth}
            className="px-3 py-1 rounded-lg bg-cyan-100 hover:bg-cyan-200 text-cyan-700 font-semibold transition-colors text-sm"
          >
            ← Prev
          </button>
          <div className="flex flex-col items-center">
            <h3 className="text-lg font-bold text-gray-900">
              {format(currentDate, 'MMMM yyyy')}
            </h3>
            <button
              onClick={goToToday}
              className="text-xs text-cyan-600 hover:text-cyan-800 underline"
            >
              Today
            </button>
          </div>
          <button
            onClick={goToNextMonth}
            className="px-3 py-1 rounded-lg bg-cyan-100 hover:bg-cyan-200 text-cyan-700 font-semibold transition-colors text-sm"
          >
            Next →
          </button>
        </div>

        {/* Calendar Grid */}
        <div className="grid grid-cols-7 gap-1 sm:gap-2">
          {/* Week day headers */}
          {weekDays.map(day => (
            <div
              key={day}
              className="text-center text-xs font-semibold text-gray-600 py-2"
            >
              {day}
            </div>
          ))}

          {/* Empty cells for days before month starts */}
          {Array.from({ length: firstDayOfWeek }).map((_, index) => (
            <div key={`empty-${index}`} className="aspect-square" />
          ))}

          {/* Calendar days */}
          {daysInMonth.map(day => {
            const total = getTotalForDay(day);
            const dayExpenses = getExpensesForDay(day);
            const isToday = isSameDay(day, new Date());

            return (
              <div
                key={day.toISOString()}
                className={`
                  aspect-square border-2 rounded-lg p-1 sm:p-2 flex flex-col items-center justify-start
                  transition-all hover:shadow-md cursor-pointer
                  ${getSpendingColor(total)}
                  ${isToday ? 'ring-2 ring-blue-500 ring-offset-2' : 'border-gray-200'}
                  ${total === 0 ? 'bg-white hover:bg-gray-50' : ''}
                `}
                title={getDayHoverLabel(day, dayExpenses, total)}
              >
                <span className={`text-xs sm:text-sm font-semibold ${isToday ? 'text-blue-700' : ''}`}>
                  {format(day, 'd')}
                </span>
                {total > 0 && (
                  <div className="flex flex-col items-center mt-1">
                    <DollarSign className="h-3 w-3 sm:h-4 sm:w-4" />
                    <span className="text-[10px] sm:text-xs font-bold">
                      {total >= 100 ? `${Math.round(total)}` : total.toFixed(0)}
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Legend */}
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-green-100 border-2 border-green-300" />
            <span className="text-gray-700">$0-20</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-yellow-100 border-2 border-yellow-300" />
            <span className="text-gray-700">$20-50</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-orange-100 border-2 border-orange-300" />
            <span className="text-gray-700">$50-100</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-red-100 border-2 border-red-300" />
            <span className="text-gray-700">$100+</span>
          </div>
        </div>

        {/* Monthly Summary */}
        <div className="mt-4 p-3 bg-gradient-to-r from-cyan-50 to-blue-50 rounded-lg border border-cyan-200">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-gray-700">
              {format(currentDate, 'MMMM')} Total:
            </span>
            <span className="text-lg font-bold text-cyan-700">
              ${expenses
                .filter(e => {
                  const expenseDate = parseLocalDate(e.date);
                  return expenseDate.getMonth() === currentDate.getMonth() &&
                         expenseDate.getFullYear() === currentDate.getFullYear();
                })
                .reduce((sum, e) => sum + e.amount, 0)
                .toFixed(2)}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
