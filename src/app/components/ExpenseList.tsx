import { Trash2 } from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { ScrollArea } from './ui/scroll-area';
import { parseLocalDate } from '../dateUtils';

interface Expense {
  id: string;
  amount: number;
  category: string;
  description: string;
  date: string;
  created_at: string;
}

interface ExpenseListProps {
  expenses: Expense[];
  onDeleteExpense: (id: string) => void;
}

export function ExpenseList({ expenses, onDeleteExpense }: ExpenseListProps) {
  const sortedExpenses = [...expenses].sort((a, b) => 
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return (
    <Card className="bg-white/85 backdrop-blur-md border-2 border-cyan-300 shadow-lg">
      <CardHeader>
        <CardTitle className="text-base sm:text-lg">Recent Expenses</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[300px] sm:h-[400px] pr-2 sm:pr-4">
          {sortedExpenses.length === 0 ? (
            <div className="text-center py-12 text-gray-500 text-sm sm:text-base">
              No expenses yet. Start adding your spending! 💸
            </div>
          ) : (
            <div className="space-y-2 sm:space-y-3">
              {sortedExpenses.map((expense) => (
                <div
                  key={expense.id}
                  className="flex items-center justify-between p-3 sm:p-4 bg-white/90 backdrop-blur-sm rounded-lg border border-cyan-200 hover:shadow-md transition-shadow"
                >
                  <div className="flex-1 min-w-0 pr-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-base sm:text-lg">{expense.category}</span>
                      <span className="font-semibold text-gray-900 text-sm sm:text-base">
                        ${expense.amount.toFixed(2)}
                      </span>
                    </div>
                    {expense.description && (
                      <p className="text-xs sm:text-sm text-gray-600 mt-1 truncate">{expense.description}</p>
                    )}
                    <p className="text-xs text-gray-500 mt-1">
                      {parseLocalDate(expense.date).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onDeleteExpense(expense.id)}
                    className="text-red-600 hover:text-red-700 hover:bg-red-50 shrink-0"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}